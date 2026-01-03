def format_currency(amount: int) -> str:
    """Format currency with dots separation (Vietnamese style).
    
    Args:
        amount (int): The amount to format.
        
    Returns:
        str: Formatted string (e.g., 1000 -> 1.000).
    """
    return "{:,}".format(amount).replace(",", ".")
