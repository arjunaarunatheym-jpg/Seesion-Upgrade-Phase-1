"""
Test Certificate Designer API Endpoints and Session Cascade Bug Fix
Tests for:
- Certificate template CRUD (GET, POST, PUT, DELETE)
- Certificate asset upload
- Session update with date/venue/programme cascade to invoices
"""
import pytest
import requests
import os
import json
from io import BytesIO

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestCertificateTemplatesAPI:
    """Certificate Template CRUD Tests"""
    
    created_template_id = None  # Class variable to store created template ID
    
    def test_01_get_certificate_templates_list(self, authenticated_client):
        """GET /api/settings/certificate-templates - returns list of templates"""
        response = authenticated_client.get(f"{BASE_URL}/api/settings/certificate-templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} existing certificate templates")
    
    def test_02_create_certificate_template(self, authenticated_client):
        """POST /api/settings/certificate-templates - saves new template"""
        template_data = {
            "name": "TEST_Classic Gold Template",
            "background": "#fffef5",
            "backgroundColor": "#fffef5",
            "borderStyle": "8px double #c9a227",
            "elements": [
                {"id": "logo", "type": "logo", "x": 50, "y": 8, "width": 100, "height": 60, "label": "Company Logo"},
                {"id": "title", "type": "text", "x": 50, "y": 20, "text": "CERTIFICATE OF COMPLETION", "fontSize": 32, "fontFamily": "Georgia", "fontWeight": "bold", "color": "#8B4513"},
                {"id": "participant", "type": "text", "x": 50, "y": 38, "text": "{Participant Name}", "fontSize": 28, "fontFamily": "Great Vibes, cursive", "color": "#1a365d"},
            ],
            "is_default": False
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/settings/certificate-templates",
            json=template_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "template" in data, "Response should contain template"
        assert data["template"]["name"] == "TEST_Classic Gold Template"
        assert "id" in data["template"], "Template should have an ID"
        assert len(data["template"]["elements"]) == 3, "Template should have 3 elements"
        
        # Store the created template ID for subsequent tests
        TestCertificateTemplatesAPI.created_template_id = data["template"]["id"]
        print(f"Created template with ID: {TestCertificateTemplatesAPI.created_template_id}")
    
    def test_03_get_specific_certificate_template(self, authenticated_client):
        """GET /api/settings/certificate-templates/{template_id} - returns specific template"""
        template_id = TestCertificateTemplatesAPI.created_template_id
        if not template_id:
            pytest.skip("No template created in previous test")
        
        response = authenticated_client.get(f"{BASE_URL}/api/settings/certificate-templates/{template_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["id"] == template_id
        assert data["name"] == "TEST_Classic Gold Template"
        assert "elements" in data
        assert "background" in data
        assert "borderStyle" in data
    
    def test_04_update_certificate_template(self, authenticated_client):
        """PUT /api/settings/certificate-templates/{template_id} - updates existing template"""
        template_id = TestCertificateTemplatesAPI.created_template_id
        if not template_id:
            pytest.skip("No template created in previous test")
        
        update_data = {
            "name": "TEST_Classic Gold Template UPDATED",
            "borderStyle": "4px solid #gold",
            "elements": [
                {"id": "logo", "type": "logo", "x": 50, "y": 10, "width": 120, "height": 70, "label": "Updated Logo"},
                {"id": "title", "type": "text", "x": 50, "y": 25, "text": "UPDATED CERTIFICATE", "fontSize": 36, "fontFamily": "Georgia", "fontWeight": "bold", "color": "#8B4513"},
            ]
        }
        
        response = authenticated_client.put(
            f"{BASE_URL}/api/settings/certificate-templates/{template_id}",
            json=update_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update persisted
        verify_response = authenticated_client.get(f"{BASE_URL}/api/settings/certificate-templates/{template_id}")
        assert verify_response.status_code == 200
        
        updated_data = verify_response.json()
        assert updated_data["name"] == "TEST_Classic Gold Template UPDATED"
        assert len(updated_data["elements"]) == 2, "Template should now have 2 elements"
        print("Template updated successfully")
    
    def test_05_delete_certificate_template(self, authenticated_client):
        """DELETE /api/settings/certificate-templates/{template_id} - deletes template"""
        template_id = TestCertificateTemplatesAPI.created_template_id
        if not template_id:
            pytest.skip("No template created in previous test")
        
        response = authenticated_client.delete(f"{BASE_URL}/api/settings/certificate-templates/{template_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        verify_response = authenticated_client.get(f"{BASE_URL}/api/settings/certificate-templates/{template_id}")
        assert verify_response.status_code == 404, "Deleted template should return 404"
        print("Template deleted successfully")
    
    def test_06_get_nonexistent_template_returns_404(self, authenticated_client):
        """GET /api/settings/certificate-templates/{invalid_id} - returns 404"""
        response = authenticated_client.get(f"{BASE_URL}/api/settings/certificate-templates/invalid-template-id-xyz")
        assert response.status_code == 404, f"Expected 404 for nonexistent template, got {response.status_code}"


class TestCertificateAssetUpload:
    """Certificate Asset Upload Tests"""
    
    def test_upload_logo_asset(self, authenticated_client, auth_token):
        """POST /api/settings/certificate-assets - uploads logo image"""
        # Create a small test image (1x1 pixel PNG)
        png_header = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D,  # IHDR chunk length
            0x49, 0x48, 0x44, 0x52,  # IHDR
            0x00, 0x00, 0x00, 0x01,  # width
            0x00, 0x00, 0x00, 0x01,  # height
            0x08, 0x02,  # bit depth, color type
            0x00, 0x00, 0x00,  # compression, filter, interlace
            0x90, 0x77, 0x53, 0xDE,  # CRC
            0x00, 0x00, 0x00, 0x0C,  # IDAT chunk length
            0x49, 0x44, 0x41, 0x54,  # IDAT
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,
            0x05, 0xFE, 0x02, 0xFE,
            0x00, 0x00, 0x00, 0x00,  # IEND chunk length
            0x49, 0x45, 0x4E, 0x44,  # IEND
            0xAE, 0x42, 0x60, 0x82   # CRC
        ])
        
        files = {
            'file': ('test_logo.png', BytesIO(png_header), 'image/png')
        }
        data = {'type': 'logo'}
        
        # Use raw requests for file upload
        response = requests.post(
            f"{BASE_URL}/api/settings/certificate-assets",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "url" in result, "Response should contain url"
        assert "filename" in result, "Response should contain filename"
        assert result["url"].startswith("/api/static/certificate_assets/")
        assert "logo_" in result["filename"]
        print(f"Asset uploaded: {result['url']}")
    
    def test_upload_signature_asset(self, authenticated_client, auth_token):
        """POST /api/settings/certificate-assets - uploads signature image"""
        # Create a small test image
        png_header = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D,
            0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01,
            0x00, 0x00, 0x00, 0x01,
            0x08, 0x02,
            0x00, 0x00, 0x00,
            0x90, 0x77, 0x53, 0xDE,
            0x00, 0x00, 0x00, 0x0C,
            0x49, 0x44, 0x41, 0x54,
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,
            0x05, 0xFE, 0x02, 0xFE,
            0x00, 0x00, 0x00, 0x00,
            0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {
            'file': ('test_signature.png', BytesIO(png_header), 'image/png')
        }
        data = {'type': 'signature'}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/certificate-assets",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "signature_" in result["filename"]
        print(f"Signature uploaded: {result['url']}")


class TestSessionUpdateCascade:
    """Test session update cascades date/venue/programme changes to invoices"""
    
    session_ids = []  # Store session IDs from context
    
    @pytest.fixture(autouse=True)
    def setup_session_ids(self):
        """Get existing session IDs from context"""
        # From context: ebe5d898 (TELAGAMAS), 21e59046 (KONE), cd64d689 (ACE GREENCEMT), 099847d9 (TELAGAMAS)
        self.session_ids = ["ebe5d898", "21e59046", "cd64d689", "099847d9"]
    
    def test_01_get_sessions_list(self, authenticated_client):
        """Verify sessions exist"""
        response = authenticated_client.get(f"{BASE_URL}/api/sessions/calendar")
        assert response.status_code == 200
        
        sessions = response.json()
        print(f"Found {len(sessions)} sessions in calendar")
        
        # Check if any of our test sessions exist
        session_names = [s.get("name", s.get("id")) for s in sessions[:5]]
        print(f"Sample session names: {session_names}")
    
    def test_02_get_session_with_invoices(self, authenticated_client):
        """Find a session that has invoices to test cascade"""
        # Get all invoices
        response = authenticated_client.get(f"{BASE_URL}/api/invoices")
        if response.status_code != 200:
            pytest.skip(f"Could not get invoices: {response.status_code}")
        
        invoices = response.json()
        print(f"Found {len(invoices)} invoices")
        
        # Find an invoice with session_id
        for invoice in invoices:
            if invoice.get("session_id"):
                session_id = invoice["session_id"]
                print(f"Found invoice {invoice.get('invoice_number')} linked to session {session_id}")
                
                # Store for next test
                TestSessionUpdateCascade.test_session_id = session_id
                TestSessionUpdateCascade.test_invoice_id = invoice.get("id")
                TestSessionUpdateCascade.original_training_dates = invoice.get("training_dates")
                TestSessionUpdateCascade.original_venue = invoice.get("venue")
                return
        
        pytest.skip("No invoices with session_id found")
    
    def test_03_update_session_dates_cascades_to_invoices(self, authenticated_client):
        """PUT /api/sessions/{session_id} - date changes cascade to invoices.training_dates"""
        session_id = getattr(TestSessionUpdateCascade, 'test_session_id', None)
        if not session_id:
            pytest.skip("No session with invoices found in previous test")
        
        # First get the session
        session_response = authenticated_client.get(f"{BASE_URL}/api/sessions/{session_id}")
        if session_response.status_code != 200:
            pytest.skip(f"Could not get session: {session_response.status_code}")
        
        session = session_response.json()
        old_start = session.get("start_date")
        old_end = session.get("end_date")
        print(f"Original dates: {old_start} to {old_end}")
        
        # Update with new dates
        new_start = "2026-03-15"
        new_end = "2026-03-16"
        
        update_data = {
            "start_date": new_start,
            "end_date": new_end
        }
        
        response = authenticated_client.put(
            f"{BASE_URL}/api/sessions/{session_id}",
            json=update_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify invoice training_dates updated
        invoice_id = TestSessionUpdateCascade.test_invoice_id
        invoice_response = authenticated_client.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        
        if invoice_response.status_code == 200:
            invoice = invoice_response.json()
            expected_dates = f"{new_start} to {new_end}"
            actual_dates = invoice.get("training_dates")
            print(f"Invoice training_dates after update: {actual_dates}")
            assert actual_dates == expected_dates, f"Expected '{expected_dates}', got '{actual_dates}'"
            print("SUCCESS: Session date change cascaded to invoice training_dates")
        
        # Restore original dates
        if old_start and old_end:
            authenticated_client.put(
                f"{BASE_URL}/api/sessions/{session_id}",
                json={"start_date": old_start, "end_date": old_end}
            )
            print(f"Restored original dates: {old_start} to {old_end}")
    
    def test_04_update_session_venue_cascades_to_invoices(self, authenticated_client):
        """PUT /api/sessions/{session_id} - venue changes cascade to invoices.venue"""
        session_id = getattr(TestSessionUpdateCascade, 'test_session_id', None)
        if not session_id:
            pytest.skip("No session with invoices found")
        
        # Get current session data
        session_response = authenticated_client.get(f"{BASE_URL}/api/sessions/{session_id}")
        if session_response.status_code != 200:
            pytest.skip(f"Could not get session: {session_response.status_code}")
        
        session = session_response.json()
        old_location = session.get("location")
        print(f"Original location: {old_location}")
        
        # Update with new venue
        new_venue = "TEST_New Training Center, Kuala Lumpur"
        
        response = authenticated_client.put(
            f"{BASE_URL}/api/sessions/{session_id}",
            json={"location": new_venue}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify invoice venue updated
        invoice_id = TestSessionUpdateCascade.test_invoice_id
        invoice_response = authenticated_client.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        
        if invoice_response.status_code == 200:
            invoice = invoice_response.json()
            actual_venue = invoice.get("venue")
            print(f"Invoice venue after update: {actual_venue}")
            assert actual_venue == new_venue, f"Expected '{new_venue}', got '{actual_venue}'"
            print("SUCCESS: Session venue change cascaded to invoice")
        
        # Restore original venue
        if old_location:
            authenticated_client.put(
                f"{BASE_URL}/api/sessions/{session_id}",
                json={"location": old_location}
            )
            print(f"Restored original location: {old_location}")


class TestAccessControl:
    """Test that certificate endpoints require authentication"""
    
    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated request to certificate templates returns 401"""
        response = requests.get(f"{BASE_URL}/api/settings/certificate-templates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
