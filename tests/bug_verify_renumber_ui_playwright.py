import re

PREVIEW_URL = "https://finance-flow-pro.preview.emergentagent.com"
EMAIL = "qa.superadmin.renumber.1785391684@mddrc.test"
PASSWORD = "QaSuper102229"
TARGET_ID = "9f0921c1-58e6-4218-8cf8-8aeb18367ce2"
TARGET_OLD_NUMBER = "INV/MDDRC/2026/01/9137"
TARGET_NEW_NUMBER = "INV/MDDRC/2026/01/9139"
DUPLICATE_NUMBER = "INV/MDDRC/2026/01/9138"
PROFORMA_ID = "7d7ae7c6-2c35-4b5c-afeb-c58481f29924"

try:
    await page.set_viewport_size({"width": 1920, "height": 1080})
    print("Step 1: Open login page")
    await page.goto(f"{PREVIEW_URL}/login", wait_until="domcontentloaded")
    await page.locator('[data-testid="login-email-input"]').fill(EMAIL)
    await page.locator('[data-testid="login-password-input"]').fill(PASSWORD)
    await page.locator('[data-testid="login-submit-button"]').click()
    await page.wait_for_function("() => !!localStorage.getItem('token')", timeout=30000)
    local_user = await page.evaluate("() => localStorage.getItem('user')")
    print(f"Login succeeded; localStorage.user is {local_user!r}")

    auth_me = await page.evaluate("""async () => {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/auth/me', {headers: {Authorization: `Bearer ${token}`}});
        return {status: res.status, data: await res.json()};
    }""")
    print(f"/auth/me returned: {auth_me}")
    if auth_me["status"] != 200 or auth_me["data"].get("role") != "super_admin":
        raise Exception(f"Expected temp user role super_admin, got {auth_me}")

    print("Step 2: Navigate directly to /finance as super_admin")
    await page.goto(f"{PREVIEW_URL}/finance", wait_until="domcontentloaded")
    await page.wait_for_selector("text=Finance Portal", timeout=30000)
    if "/login" in page.url:
        raise Exception("Super_admin was redirected to login instead of Finance Dashboard")
    print(f"Finance page loaded at {page.url}")

    print("Step 3: Open Invoices tab")
    await page.get_by_role("tab", name="Invoices", exact=True).click()
    await page.wait_for_selector("text=Invoice Management", timeout=30000)
    await page.wait_for_selector(f'[data-testid="renumber-invoice-{TARGET_ID}"]', timeout=30000)

    print("Step 4: Compare API invoice rows to rendered renumber buttons")
    button_check = await page.evaluate(f"""async () => {{
        const token = localStorage.getItem('token');
        const res = await fetch('/api/finance/invoices?year=2026', {{headers: {{Authorization: `Bearer ${{token}}`}}}});
        const data = await res.json();
        const nonProforma = data.filter(i => i.document_type !== 'proforma');
        const proformas = data.filter(i => i.document_type === 'proforma');
        const missingRenumber = nonProforma
          .filter(i => !document.querySelector(`[data-testid="renumber-invoice-${{i.id}}"]`))
          .map(i => ({{id: i.id, invoice_number: i.invoice_number, document_type: i.document_type || null}}));
        const proformaWithRenumber = proformas
          .filter(i => document.querySelector(`[data-testid="renumber-invoice-${{i.id}}"]`))
          .map(i => ({{id: i.id, invoice_number: i.invoice_number}}));
        return {{
          status: res.status,
          total: data.length,
          nonProformaCount: nonProforma.length,
          proformaCount: proformas.length,
          missingRenumber,
          proformaWithRenumber,
          seededTargetHasButton: !!document.querySelector('[data-testid="renumber-invoice-{TARGET_ID}"]'),
          seededDuplicateHasButton: !!data.find(i => i.invoice_number === '{DUPLICATE_NUMBER}') || false,
          seededProformaHasButton: !!document.querySelector('[data-testid="renumber-invoice-{PROFORMA_ID}"]'),
          seededProformaBadge: !!document.querySelector('[data-testid="proforma-badge-{PROFORMA_ID}"]')
        }};
    }}""")
    print(f"Renumber button check: {button_check}")
    if button_check["status"] != 200:
        raise Exception(f"Invoice API failed in browser: {button_check}")
    if button_check["missingRenumber"]:
        raise Exception(f"Non-proforma rows missing renumber buttons: {button_check['missingRenumber'][:5]}")
    if button_check["proformaWithRenumber"] or button_check["seededProformaHasButton"]:
        raise Exception(f"Proforma rows incorrectly have renumber buttons: {button_check}")
    if not button_check["seededProformaBadge"]:
        raise Exception("Seeded proforma row/badge was not rendered")

    print("Step 5: Open renumber dialog and verify fields")
    await page.locator(f'[data-testid="renumber-invoice-{TARGET_ID}"]').click()
    dialog = page.locator('[data-testid="renumber-invoice-dialog"]')
    await dialog.wait_for(state="visible", timeout=10000)
    dialog_text = await dialog.inner_text()
    print(f"Dialog text includes current details: {dialog_text[:300]}")
    if TARGET_OLD_NUMBER not in dialog_text:
        raise Exception("Dialog did not show current invoice number")
    for testid in ["renumber-new-number-input", "renumber-reason-input", "renumber-confirm-checkbox", "renumber-submit-btn"]:
        count = await page.locator(f'[data-testid="{testid}"]').count()
        print(f"Field {testid} count={count}")
        if count != 1:
            raise Exception(f"Expected exactly one {testid}, found {count}")
    submit_btn = page.locator('[data-testid="renumber-submit-btn"]')
    if await submit_btn.is_enabled():
        raise Exception("Renumber submit button should be disabled initially")

    print("Step 6: Fill valid renumber form and submit")
    await page.locator('[data-testid="renumber-new-number-input"]').fill(TARGET_NEW_NUMBER)
    await page.locator('[data-testid="renumber-reason-input"]').fill("QA renumber verification reason")
    await page.locator('[data-testid="renumber-confirm-checkbox"]').check()
    await page.wait_for_timeout(200)
    if not await submit_btn.is_enabled():
        raise Exception("Submit button did not enable after valid form input")
    async with page.expect_response(lambda resp: f"/api/finance/invoices/{TARGET_ID}/renumber" in resp.url and resp.request.method == "POST", timeout=15000) as resp_info:
        await submit_btn.click()
    success_resp = await resp_info.value
    success_body = await success_resp.json()
    print(f"Renumber response: status={success_resp.status}, body={success_body}")
    if success_resp.status != 200:
        raise Exception(f"Expected successful renumber response, got {success_resp.status}: {success_body}")
    await page.get_by_text(re.compile("renumbered", re.I)).first.wait_for(timeout=5000)
    await dialog.wait_for(state="hidden", timeout=10000)
    await page.wait_for_function(f"() => document.body.innerText.includes('{TARGET_NEW_NUMBER}')", timeout=15000)

    verify_update = await page.evaluate(f"""async () => {{
        const token = localStorage.getItem('token');
        const res = await fetch('/api/finance/invoices?year=2026', {{headers: {{Authorization: `Bearer ${{token}}`}}}});
        const data = await res.json();
        const inv = data.find(i => i.id === '{TARGET_ID}');
        return {{status: res.status, invoice_number: inv && inv.invoice_number}};
    }}""")
    print(f"Post-refresh invoice check: {verify_update}")
    if verify_update.get("invoice_number") != TARGET_NEW_NUMBER:
        raise Exception(f"List/API did not refresh to new invoice number: {verify_update}")

    print("Step 7: Submit duplicate number and verify user-visible error")
    await page.locator(f'[data-testid="renumber-invoice-{TARGET_ID}"]').click()
    await dialog.wait_for(state="visible", timeout=10000)
    await page.locator('[data-testid="renumber-new-number-input"]').fill(DUPLICATE_NUMBER)
    await page.locator('[data-testid="renumber-reason-input"]').fill("QA duplicate number error check")
    await page.locator('[data-testid="renumber-confirm-checkbox"]').check()
    await page.wait_for_timeout(200)
    async with page.expect_response(lambda resp: f"/api/finance/invoices/{TARGET_ID}/renumber" in resp.url and resp.request.method == "POST", timeout=15000) as dup_resp_info:
        await page.locator('[data-testid="renumber-submit-btn"]').click()
    dup_resp = await dup_resp_info.value
    try:
        dup_body = await dup_resp.json()
    except Exception:
        dup_body = {"raw": await dup_resp.text()}
    print(f"Duplicate renumber response: status={dup_resp.status}, body={dup_body}")
    if dup_resp.status != 400:
        raise Exception(f"Expected duplicate renumber to return 400, got {dup_resp.status}")
    await page.get_by_text(re.compile("already used", re.I)).first.wait_for(timeout=5000)
    print("Duplicate error toast is visible")

    # Get error messages using specific selectors
    error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")

    print("SUCCESS: Focused renumber UI verification passed for super_admin role")
except Exception as e:
    print(f"FAILURE: {e}")
    await page.screenshot(path="/app/test_reports/bug_verify_renumber_ui_failure.jpg", quality=40, full_page=False)
    raise