"""
Playwright checklist mirrored in the browser automation tool for the focused
invoice renumber UI bug verification. The executable browser script is passed
to mcp_browser_automation, but this file records the tested flow for handoff.
"""

FLOW = """
1. Clear localStorage and open the preview URL.
2. Login as arjuna@mddrc.com.my / Dana102229.
3. Inspect localStorage for token and user keys after login.
4. Navigate to /finance, open the Invoices tab, and count buttons matching
   [data-testid^='renumber-invoice-'].
5. If buttons exist, open the first one and verify dialog fields and disabled
   submit state. If no buttons exist, report that the user-visible UI button is
   not available in the normal login flow.
"""

print(FLOW)