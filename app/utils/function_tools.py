"""
Function tools for OpenAI Realtime API integration with Telnyx
Handles call ending and call transfer functionality
"""
import json
import logging
from typing import Dict, Any
from .telnyx_http import telnyx_cmd

logger = logging.getLogger(__name__)

# Store call states to track pending operations
call_states = {}

def get_departments():
    """Get department configuration from agent_config"""
    try:
        from ..agent_config import DEPARTMENTS
        return DEPARTMENTS
    except ImportError:
        logger.error("Could not import DEPARTMENTS from agent_config")
        return {}

def get_function_tools():
    """
    Returns the function tools configuration for OpenAI Realtime API
    Only includes tools if departments are properly configured
    """
    departments = get_departments()
    tools = []
    
    # Always include end_call function
    tools.append({
        "type": "function",
        "name": "end_call",
        "description": "End the current phone call when the caller wants to hang up or the conversation is complete.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "The reason for ending the call",
                    "enum": ["conversation_complete", "caller_request", "escalation_needed"]
                }
            },
            "required": ["reason"]
        }
    })
    
    # Only include transfer_call function if departments are configured
    if departments and len(departments) > 0:
        department_names = list(departments.keys())
        tools.append({
            "type": "function", 
            "name": "transfer_call",
            "description": "Transfer the call to a different department or extension when the caller needs specialized assistance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "The department to transfer the call to",
                        "enum": department_names
                    },
                    "reason": {
                        "type": "string", 
                        "description": "The reason for the transfer"
                    }
                },
                "required": ["department", "reason"]
            }
        })
    
    return tools

async def handle_function_call(
    func_name: str, 
    func_args: Dict[str, Any], 
    call_control_id: str, 
    telnyx_api_key: str
) -> str:
    """
    Handle function calls from OpenAI Realtime API
    
    Args:
        func_name: Name of the function being called
        func_args: Arguments passed to the function
        call_control_id: Telnyx call control ID
        telnyx_api_key: Telnyx API key
        
    Returns:
        Response message to be sent back to the AI
    """
    try:
        # Check if there's already a pending operation for this call
        existing_state = call_states.get(call_control_id, {})
        
        if func_name == "end_call":
            # Don't allow end_call if there's already a pending transfer
            if existing_state.get("pending_transfer"):
                logger.info(f"Ignoring end_call for {call_control_id} - transfer already pending")
                return "Transfer is already in progress."
            # Don't allow duplicate end_call requests
            if existing_state.get("pending_hangup"):
                logger.info(f"Ignoring duplicate end_call for {call_control_id} - hangup already pending")
                return "Call is already ending."
            return await handle_end_call(func_args, call_control_id, telnyx_api_key)
        elif func_name == "transfer_call":
            # Don't allow transfer if there's already a pending hangup
            if existing_state.get("pending_hangup"):
                logger.info(f"Ignoring transfer_call for {call_control_id} - hangup already pending")
                return "Call is already ending."
            # Don't allow duplicate transfer calls
            if existing_state.get("pending_transfer"):
                existing_dept = existing_state.get("department")
                new_dept = func_args.get("department")
                if existing_dept == new_dept:
                    logger.info(f"Ignoring duplicate transfer_call for {call_control_id} - transfer to {new_dept} already pending")
                    return "Transfer is already in progress."
                else:
                    logger.info(f"Updating transfer destination from {existing_dept} to {new_dept}")
                    # Allow the new transfer call to override the previous one
            return await handle_transfer_call(func_args, call_control_id, telnyx_api_key)
        else:
            logger.error(f"Unknown function called: {func_name}")
            return "I'm sorry, I couldn't process that request."
            
    except Exception as e:
        logger.error(f"Error handling function call {func_name}: {e}")
        return "I'm sorry, there was an error processing your request."

async def handle_end_call(func_args: Dict[str, Any], call_control_id: str, telnyx_api_key: str) -> str:
    """
    Handle end call function
    
    Args:
        func_args: Function arguments containing reason
        call_control_id: Telnyx call control ID
        telnyx_api_key: Telnyx API key
        
    Returns:
        Response message for the AI
    """
    reason = func_args.get("reason", "conversation_complete")
    
    # Mark call for hangup (don't hang up immediately to allow final response)
    call_states[call_control_id] = {
        "pending_hangup": True,
        "reason": reason
    }
    
    logger.info(f"Marked call {call_control_id} for hangup with reason: {reason}")
    
    # Return appropriate goodbye message based on reason
    if reason == "caller_request":
        return "Thank you for calling! Have a wonderful day!"
    elif reason == "escalation_needed":
        return "I'll connect you with someone who can better assist you. Thank you for your patience!"
    else:
        return "Thank you so much for calling! Have a great day!"

async def handle_transfer_call(func_args: Dict[str, Any], call_control_id: str, telnyx_api_key: str) -> str:
    """
    Handle transfer call function
    
    Args:
        func_args: Function arguments containing department and reason
        call_control_id: Telnyx call control ID  
        telnyx_api_key: Telnyx API key
        
    Returns:
        Response message for the AI
    """
    department = func_args.get("department")
    reason = func_args.get("reason", "Customer requested transfer")
    
    # Get department configuration
    departments = get_departments()
    
    if not department or department not in departments:
        available_depts = ", ".join(departments.keys()) if departments else "sales, support, billing, technical, management"
        logger.error(f"No configuration found for department: {department}")
        return f"I'm sorry, I couldn't find the {department} department. Available departments are: {available_depts}. Let me connect you with our main support team instead."
    
    dept_config = departments[department]
    destination = dept_config.get("sip_uri")
    headers = dept_config.get("headers", [])
    
    if not destination:
        logger.error(f"No SIP URI configured for department: {department}")
        return f"I'm sorry, there's a configuration issue with the {department} department. Let me connect you with our main support team instead."
    
    # Mark call for transfer (don't transfer immediately to allow final response)
    call_states[call_control_id] = {
        "pending_transfer": True,
        "department": department,
        "destination": destination,
        "headers": headers,
        "reason": reason
    }
    
    logger.info(f"Marked call {call_control_id} for transfer to {department} department")
    
    return f"Perfect! I'm transferring your call to our {department} department now. Please hold on for just a moment while I connect you."

async def execute_pending_operation(call_control_id: str, telnyx_api_key: str):
    """
    Execute pending call operations (hangup or transfer) after AI response is complete
    
    Args:
        call_control_id: Telnyx call control ID
        telnyx_api_key: Telnyx API key
    """
    if call_control_id not in call_states:
        return
        
    state = call_states[call_control_id]
    
    # Check if already executed to prevent duplicates
    if state.get("executed"):
        logger.info(f"Pending operation for {call_control_id} already executed")
        return
    
    # Mark as executed to prevent duplicate execution
    state["executed"] = True
    
    try:
        # Always prioritize transfer over hangup
        if state.get("pending_transfer"):
            department = state.get("department")
            destination = state.get("destination")
            headers = state.get("headers", [])
            
            logger.info(f"Executing transfer for call {call_control_id} to {department}")
            
            # Create transfer payload
            transfer_payload = {
                "to": destination,
                "timeout_secs": 30,
                "time_limit_secs": 3600
            }
            
            # Add SIP headers if configured
            if headers:
                transfer_payload["sip_headers"] = headers
            
            # Execute the transfer
            response = await telnyx_cmd(call_control_id, "transfer", telnyx_api_key, transfer_payload)
            
            if response.is_success:
                logger.info(f"Successfully transferred call {call_control_id} to {department}")
            else:
                logger.error(f"Transfer failed for call {call_control_id}: {response.status_code} {response.text}")
                # If transfer fails, hang up the call
                await telnyx_cmd(call_control_id, "hangup", telnyx_api_key)
                
        elif state.get("pending_hangup"):
            logger.info(f"Executing hangup for call {call_control_id}")
            await telnyx_cmd(call_control_id, "hangup", telnyx_api_key)
                
    except Exception as e:
        logger.error(f"Error executing pending operation for call {call_control_id}: {e}")
        # On error, try to hang up the call gracefully
        try:
            await telnyx_cmd(call_control_id, "hangup", telnyx_api_key)
        except Exception as hangup_error:
            logger.error(f"Error hanging up call {call_control_id} after operation error: {hangup_error}")
    
    finally:
        # Clean up call state
        if call_control_id in call_states:
            del call_states[call_control_id]

def has_pending_operation(call_control_id: str) -> bool:
    """
    Check if a call has pending operations
    
    Args:
        call_control_id: Telnyx call control ID
        
    Returns:
        True if call has pending operations
    """
    if call_control_id not in call_states:
        return False
        
    state = call_states[call_control_id]
    return state.get("pending_hangup", False) or state.get("pending_transfer", False)
