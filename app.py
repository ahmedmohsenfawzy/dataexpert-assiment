import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from urllib.parse import urlparse

# Page configuration
st.set_page_config(
    page_title="Support Ticket System",
    page_icon="🎫",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_db_connection():
    """Establish connection to Lakebase Postgres database (dataexpert-assiment)"""
    try:
        # Get Lakebase URL from environment secrets
        lakebase_url = os.environ.get('lakebase-url')
        if not lakebase_url:
            st.error("❌ Lakebase URL not found. Please configure the 'lakebase-url' secret.")
            return None
        
        # Parse the connection URL
        parsed = urlparse(lakebase_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables if they don't exist"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            # Create tickets table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create messages table with foreign key to tickets
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            return True
    except Exception as e:
        st.error(f"❌ Database initialization error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_tickets():
    """Fetch all tickets from the database"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, description, status, created_at, updated_at
                FROM tickets
                ORDER BY updated_at DESC
            """)
            tickets = cur.fetchall()
            return tickets
    except Exception as e:
        st.error(f"❌ Error fetching tickets: {e}")
        return []
    finally:
        conn.close()

def get_ticket_messages(ticket_id):
    """Fetch all messages for a specific ticket"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, message, created_at
                FROM messages
                WHERE ticket_id = %s
                ORDER BY created_at ASC
            """, (ticket_id,))
            messages = cur.fetchall()
            return messages
    except Exception as e:
        st.error(f"❌ Error fetching messages: {e}")
        return []
    finally:
        conn.close()

def create_ticket(title, description):
    """Create a new support ticket"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tickets (title, description, status)
                VALUES (%s, %s, 'open')
                RETURNING id
            """, (title, description))
            ticket_id = cur.fetchone()[0]
            conn.commit()
            return ticket_id
    except Exception as e:
        st.error(f"❌ Error creating ticket: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def add_message(ticket_id, message):
    """Add a message to an existing ticket"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            # Insert the message
            cur.execute("""
                INSERT INTO messages (ticket_id, message)
                VALUES (%s, %s)
            """, (ticket_id, message))
            
            # Update ticket's updated_at timestamp
            cur.execute("""
                UPDATE tickets
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (ticket_id,))
            
            conn.commit()
            return True
    except Exception as e:
        st.error(f"❌ Error adding message: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_ticket_status(ticket_id, new_status):
    """Update the status of a ticket"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tickets
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (new_status, ticket_id))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"❌ Error updating ticket status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_ticket_stats():
    """Get ticket statistics"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'open' THEN 1 END) as open,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed
                FROM tickets
            """)
            stats = cur.fetchone()
            return stats
    except Exception as e:
        st.error(f"❌ Error fetching stats: {e}")
        return {}
    finally:
        conn.close()

# Initialize database
if init_database():
    st.success("✅ Connected to Lakebase database (dataexpert-assiment)")
else:
    st.error("❌ Failed to initialize database. Please check your connection.")
    st.stop()

# Main app header
st.title("🎫 Support Ticket Management System")
st.markdown("**Connected to Lakebase:** `dataexpert-assiment`")

# Show statistics
stats = get_ticket_stats()
if stats:
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Tickets", stats.get('total', 0))
    with col2:
        st.metric("Open", stats.get('open', 0))
    with col3:
        st.metric("In Progress", stats.get('in_progress', 0))
    with col4:
        st.metric("Resolved", stats.get('resolved', 0))
    with col5:
        st.metric("Closed", stats.get('closed', 0))

st.divider()

# Sidebar navigation
page = st.sidebar.radio(
    "📋 Navigation",
    ["View All Tickets", "Create New Ticket"]
)

# ====================
# VIEW ALL TICKETS PAGE
# ====================
if page == "View All Tickets":
    st.header("📋 All Support Tickets")
    
    tickets = get_all_tickets()
    
    if not tickets:
        st.info("ℹ️ No tickets found. Create your first ticket using the sidebar!")
    else:
        # Filter by status
        col1, col2 = st.columns([3, 1])
        with col2:
            status_filter = st.selectbox(
                "Filter by status",
                ["All", "open", "in_progress", "resolved", "closed"]
            )
        
        filtered_tickets = tickets if status_filter == "All" else [
            t for t in tickets if t['status'] == status_filter
        ]
        
        st.info(f"Showing {len(filtered_tickets)} ticket(s)")
        
        # Display each ticket
        for ticket in filtered_tickets:
            status_emoji = {
                "open": "🆕",
                "in_progress": "⏳",
                "resolved": "✅",
                "closed": "🔒"
            }.get(ticket['status'], "❓")
            
            with st.expander(
                f"{status_emoji} Ticket #{ticket['id']} - {ticket['title']} [{ticket['status'].upper()}]",
                expanded=False
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown("**Description:**")
                    st.write(ticket['description'] or "_No description provided_")
                    st.caption(f"📅 Created: {ticket['created_at']} | 🔄 Updated: {ticket['updated_at']}")
                
                with col2:
                    st.markdown("**Update Status:**")
                    new_status = st.selectbox(
                        "Status",
                        ["open", "in_progress", "resolved", "closed"],
                        index=["open", "in_progress", "resolved", "closed"].index(ticket['status']),
                        key=f"status_{ticket['id']}",
                        label_visibility="collapsed"
                    )
                    
                    if st.button("💾 Update Status", key=f"update_{ticket['id']}", use_container_width=True):
                        if update_ticket_status(ticket['id'], new_status):
                            st.success("✅ Status updated!")
                            st.rerun()
                
                # Messages section
                st.divider()
                st.subheader("💬 Conversation")
                
                messages = get_ticket_messages(ticket['id'])
                
                if messages:
                    for idx, msg in enumerate(messages, 1):
                        with st.container():
                            st.markdown(f"**Message #{idx}** · _{msg['created_at']}_")
                            st.info(msg['message'])
                else:
                    st.caption("_No messages yet. Add one below._")
                
                # Add new message form
                st.markdown("**➕ Add New Message:**")
                with st.form(key=f"add_message_{ticket['id']}"):
                    new_message = st.text_area(
                        "Message",
                        placeholder="Type your message here...",
                        height=100,
                        label_visibility="collapsed",
                        key=f"new_msg_{ticket['id']}"
                    )
                    submit_message = st.form_submit_button("📤 Send Message", use_container_width=True)
                    
                    if submit_message:
                        if not new_message.strip():
                            st.error("❌ Message cannot be empty")
                        else:
                            if add_message(ticket['id'], new_message):
                                st.success("✅ Message added!")
                                st.rerun()

# ====================
# CREATE NEW TICKET PAGE
# ====================
elif page == "Create New Ticket":
    st.header("➕ Create New Support Ticket")
    
    with st.form(key="create_ticket_form"):
        st.markdown("Fill in the details below to create a new support ticket:")
        
        title = st.text_input(
            "Ticket Title *",
            placeholder="e.g., Unable to login to account",
            help="A brief summary of the issue"
        )
        
        description = st.text_area(
            "Detailed Description",
            placeholder="Provide more details about your issue...",
            height=200,
            help="Explain the problem in detail"
        )
        
        st.divider()
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit = st.form_submit_button("🎫 Create Ticket", use_container_width=True)
        
        if submit:
            if not title.strip():
                st.error("❌ Please provide a ticket title")
            else:
                ticket_id = create_ticket(title, description)
                if ticket_id:
                    st.success(f"✅ Ticket #{ticket_id} created successfully!")
                    st.balloons()
                    st.info("👉 Go to 'View All Tickets' to see your new ticket and add messages.")

# Footer
st.sidebar.divider()
st.sidebar.markdown("""---
**Powered by:**
- 🚀 Databricks Apps
- 🗄️ Lakebase PostgreSQL
- 🎨 Streamlit
""")