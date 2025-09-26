import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import time

# Configure the page
st.set_page_config(
    page_title="MCP Workflow System",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

def test_connection():
    """Test if the API is reachable"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException:
        return False, None

def make_api_call(endpoint, method="GET", data=None):
    """Make API call with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        return response.status_code, response.json() if response.text else {}
    except requests.exceptions.RequestException as e:
        return 500, {"error": str(e)}

def main():
    # Header
    st.markdown('<div class="main-header">🔧 MCP Workflow System Dashboard</div>', unsafe_allow_html=True)
    
    # Connection status
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Check Connection", use_container_width=True):
            with st.spinner("Testing connection..."):
                connected, system_info = test_connection()
                
                if connected:
                    st.markdown(f'<div class="success-box">✅ Connected successfully! System: {system_info.get("message", "Unknown")}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="error-box">❌ Cannot connect to API. Make sure the server is running on localhost:8000</div>', unsafe_allow_html=True)
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio(
        "Select Mode",
        ["System Status", "Chat Interface", "Maintenance Workflow", "API Explorer"]
    )
    
    # Main content based on selection
    if app_mode == "System Status":
        show_system_status()
    elif app_mode == "Chat Interface":
        show_chat_interface()
    elif app_mode == "Maintenance Workflow":
        show_maintenance_workflow()
    elif app_mode == "API Explorer":
        show_api_explorer()

def show_system_status():
    st.header("📊 System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Status", key="refresh_status"):
            with st.spinner("Checking system status..."):
                status_code, response = make_api_call("/api/status")
                
                if status_code == 200:
                    st.markdown('<div class="success-box">✅ System status retrieved successfully</div>', unsafe_allow_html=True)
                    
                    # Overall status
                    overall_status = response.get("overall_status", "unknown")
                    status_color = "🟢" if overall_status == "healthy" else "🟡" if overall_status == "degraded" else "🔴"
                    st.metric("Overall System Status", f"{status_color} {overall_status.upper()}")
                    
                    # Systems table
                    systems = response.get("systems", {})
                    if systems:
                        systems_data = []
                        for name, info in systems.items():
                            systems_data.append({
                                "System": name.upper(),
                                "Status": info.get("status", "unknown"),
                                "Message": info.get("message", "No message"),
                                "Response Time": f"{info.get('response_time', 0):.3f}s" if info.get('response_time') else "N/A"
                            })
                        
                        df = pd.DataFrame(systems_data)
                        st.dataframe(df, use_container_width=True)
                else:
                    st.markdown(f'<div class="error-box">❌ Error retrieving status: {response.get("error", "Unknown error")}</div>', unsafe_allow_html=True)
    
    with col2:
        st.subheader("Available Systems")
        systems_list = [
            {"name": "Inventory", "type": "SQL Server", "status": "🟢"},
            {"name": "Workorders", "type": "Oracle Database", "status": "🟢"},
            {"name": "Permits", "type": ".NET Core API", "status": "🟡"},
            {"name": "HR", "type": "Excel Data", "status": "🟢"}
        ]
        
        for system in systems_list:
            st.write(f"{system['status']} **{system['name']}** ({system['type']})")

def show_chat_interface():
    st.header("💬 Chat Interface")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about maintenance, inventory, or system status..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                status_code, response = make_api_call(
                    "/api/chat", 
                    "POST", 
                    {"message": prompt, "user_id": "streamlit_user"}
                )
                
                if status_code == 200:
                    ai_response = response.get("response", "No response received")
                    st.markdown(ai_response)
                    
                    # Show additional details if available
                    if response.get("requires_approval"):
                        st.info(f"📋 Approval required: {response.get('approval_code', 'Unknown')}")
                    
                    if response.get("actions"):
                        st.write("**Actions taken:**")
                        for action in response.get("actions", []):
                            st.write(f"• {action}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                else:
                    error_msg = f"Error: {response.get('error', 'Unknown error')}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Clear chat button
    if st.button("Clear Chat History", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

def show_maintenance_workflow():
    st.header("🔧 Maintenance Workflow")
    
    with st.form("maintenance_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            equipment_id = st.text_input("Equipment ID", placeholder="e.g., PUMP-001, COMPRESSOR-002")
            priority = st.selectbox("Priority", ["low", "medium", "high", "critical"])
        
        with col2:
            issue_description = st.text_area(
                "Issue Description", 
                placeholder="Describe the issue in detail...",
                height=100
            )
            requested_by = st.text_input("Requested By", value="Maintenance Team")
        
        submitted = st.form_submit_button("🚀 Submit Maintenance Request")
        
        if submitted:
            if not equipment_id or not issue_description:
                st.error("Please fill in all required fields")
            else:
                with st.spinner("Processing maintenance request..."):
                    request_data = {
                        "equipment_id": equipment_id,
                        "issue_description": issue_description,
                        "priority": priority,
                        "requested_by": requested_by
                    }
                    
                    status_code, response = make_api_call(
                        "/api/workflow/maintenance", 
                        "POST", 
                        request_data
                    )
                    
                    if status_code == 200:
                        st.markdown('<div class="success-box">✅ Maintenance request submitted successfully!</div>', unsafe_allow_html=True)
                        
                        # Display response details
                        st.subheader("Response Details")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Workflow ID:** {response.get('workflow_id', 'N/A')}")
                            st.write(f"**Message:** {response.get('message', 'No message')}")
                        
                        with col2:
                            st.write(f"**Requires Approval:** {'✅ Yes' if response.get('requires_approval') else '❌ No'}")
                            if response.get('approval_code'):
                                st.write(f"**Approval Code:** `{response.get('approval_code')}`")
                        
                        # Show details if available
                        if response.get('details'):
                            with st.expander("Detailed Information"):
                                st.json(response['details'])
                    else:
                        st.markdown(f'<div class="error-box">❌ Error submitting request: {response.get("error", "Unknown error")}</div>', unsafe_allow_html=True)

def show_api_explorer():
    st.header("🔍 API Explorer")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Available Endpoints")
        
        endpoints = [
            {"method": "GET", "path": "/", "description": "Root endpoint"},
            {"method": "GET", "path": "/api/status", "description": "System status"},
            {"method": "POST", "path": "/api/chat", "description": "Chat interface"},
            {"method": "POST", "path": "/api/workflow/maintenance", "description": "Maintenance workflow"},
            {"method": "GET", "path": "/api/systems", "description": "List systems"}
        ]
        
        for endpoint in endpoints:
            st.code(f"{endpoint['method']} {endpoint['path']}")
            st.caption(endpoint['description'])
            st.divider()
    
    with col2:
        st.subheader("Test Endpoint")
        
        selected_endpoint = st.selectbox(
            "Select endpoint to test",
            [f"{ep['method']} {ep['path']}" for ep in endpoints]
        )
        
        if st.button("Test Endpoint", key="test_endpoint"):
            method, path = selected_endpoint.split(" ", 1)
            
            with st.spinner(f"Testing {method} {path}..."):
                status_code, response = make_api_call(
                    path, 
                    method,
                    {"test": "data"} if method == "POST" else None
                )
                
                st.write(f"**Status Code:** {status_code}")
                
                if status_code == 200:
                    st.markdown('<div class="success-box">✅ Request successful</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="error-box">❌ Request failed</div>', unsafe_allow_html=True)
                
                st.subheader("Response")
                st.json(response)

if __name__ == "__main__":
    main()
