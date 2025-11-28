"""Background task definitions for asynchronous processing."""

import time
from celery import Task
from app.core.celery_app import celery_app


@celery_app.task(name="send_transaction_email", bind=True)
def send_transaction_email(
    self: Task,
    email: str,
    amount: str,
    status: str
) -> dict:
    """
    Send email notification about transaction.
    
    Simulates slow SMTP server with configurable delay.
    In production, this would use an email service like SendGrid or AWS SES.
    
    Args:
        email: Recipient email address
        amount: Transaction amount as string (e.g., "100.5000")
        status: Transaction status ("SUCCESS" or "FAILED")
        
    Returns:
        dict: Result with success status and message
    """
    # Simulate slow SMTP server (2 seconds)
    time.sleep(2)
    
    # Log the email (in production, actually send email)
    message = f"Sending email to {email}: Transfer {amount} {status}"
    print(f"[EMAIL TASK {self.request.id}] {message}")
    
    return {
        "success": True,
        "message": message,
        "task_id": self.request.id
    }


@celery_app.task(name="audit_log_transaction", bind=True)
def audit_log_transaction(
    self: Task,
    transaction_id: str,
    data: dict
) -> dict:
    """
    Write transaction to audit log system.
    
    Simulates writing to external audit system with configurable delay.
    In production, this would write to a separate audit database or service.
    
    Args:
        transaction_id: UUID of the transaction
        data: Transaction data dictionary with keys:
            - sender_wallet_id: UUID string
            - receiver_wallet_id: UUID string
            - amount: Decimal string
            - status: Status string
            - created_at: ISO timestamp string
            
    Returns:
        dict: Result with success status and message
    """
    # Simulate slow audit system write (1 second)
    time.sleep(1)
    
    # Log the audit entry (in production, write to audit system)
    message = f"Audit log for transaction {transaction_id}: {data}"
    print(f"[AUDIT TASK {self.request.id}] {message}")
    
    return {
        "success": True,
        "message": message,
        "task_id": self.request.id,
        "transaction_id": transaction_id
    }
