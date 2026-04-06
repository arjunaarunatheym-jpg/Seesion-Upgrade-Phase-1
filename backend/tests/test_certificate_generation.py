"""
Certificate Generation API Tests
Tests for:
- GET /api/certificates/font-settings - returns default or saved font settings
- PUT /api/certificates/font-settings - saves font settings to DB
- POST /api/certificates/preview-pdf/{session_id}/{participant_id} - generates certificate preview as PNG
- POST /api/certificates/generate-pdf/{session_id}/{participant_id}?force=true - generates real certificate PDF
- POST /api/certificates/generate-bulk-pdf/{session_id}?force=true - bulk generates for all participants
- Certificate number format: MDDRC/COA/YYYY/MM/XXXXX
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data from agent context
TEST_SESSION_ID = "cd64d689-5d51-4368-86fe-3d3739b9343c"  # DEFENSIVE DRIVING session
TEST_PARTICIPANT_ID = "b849a437-1296-4137-b43a-ac399a6ae84e"  # MOHD KHAIRUL BIN MAHAMOOD

# Admin credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

# Coordinator credentials
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def coordinator_token():
    """Get coordinator authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": COORDINATOR_EMAIL,
        "password": COORDINATOR_PASSWORD
    })
    assert response.status_code == 200, f"Coordinator login failed: {response.text}"
    return response.json().get("access_token")


@pytest.fixture
def admin_client(admin_token):
    """Requests session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


@pytest.fixture
def coordinator_client(coordinator_token):
    """Requests session with coordinator auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {coordinator_token}"
    })
    return session


class TestFontSettingsAPI:
    """Tests for certificate font settings endpoints"""
    
    def test_get_font_settings_admin(self, admin_client):
        """GET /api/certificates/font-settings - Admin can get font settings"""
        response = admin_client.get(f"{BASE_URL}/api/certificates/font-settings")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify default settings structure
        assert "participant_name" in data
        assert "ic_number" in data
        assert "company_name" in data
        assert "certificate_title" in data
        assert "top_margin" in data
        assert "paragraph_spacing" in data
        
        # Verify field structure
        assert "font_size" in data["participant_name"]
        assert "max_lines" in data["participant_name"]
        assert "auto_fit" in data["participant_name"]
        print(f"Font settings retrieved: {list(data.keys())}")
    
    def test_get_font_settings_coordinator(self, coordinator_client):
        """GET /api/certificates/font-settings - Coordinator can get font settings"""
        response = coordinator_client.get(f"{BASE_URL}/api/certificates/font-settings")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "participant_name" in data
        print("Coordinator can access font settings")
    
    def test_put_font_settings_admin(self, admin_client):
        """PUT /api/certificates/font-settings - Admin can save font settings"""
        test_settings = {
            "participant_name": {"font_size": 18, "max_lines": 1, "auto_fit": True, "bold": True},
            "ic_number": {"font_size": 14, "max_lines": 1, "auto_fit": False, "bold": False},
            "company_name": {"font_size": 12, "max_lines": 1, "auto_fit": True, "bold": False},
            "certificate_title": {"font_size": 16, "max_lines": 2, "auto_fit": True, "bold": True},
            "certificate_subtitle": {"font_size": 12, "max_lines": 1, "auto_fit": True, "bold": False},
            "dates": {"font_size": 10, "max_lines": 1, "auto_fit": True, "bold": False},
            "venue": {"font_size": 8, "max_lines": 2, "auto_fit": True, "bold": False},
            "certificate_number": {"font_size": 10, "max_lines": 1, "auto_fit": False, "bold": False},
            "top_margin": 75,
            "paragraph_spacing": 60
        }
        
        response = admin_client.put(f"{BASE_URL}/api/certificates/font-settings", json=test_settings)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert data["message"] == "Font settings saved"
        print("Font settings saved successfully")
        
        # Verify settings were saved by fetching them
        get_response = admin_client.get(f"{BASE_URL}/api/certificates/font-settings")
        assert get_response.status_code == 200
        saved_data = get_response.json()
        assert saved_data["top_margin"] == 75
        assert saved_data["paragraph_spacing"] == 60
        print("Verified settings were persisted")
    
    def test_put_font_settings_coordinator(self, coordinator_client):
        """PUT /api/certificates/font-settings - Coordinator can save font settings"""
        test_settings = {
            "top_margin": 80,
            "paragraph_spacing": 65
        }
        
        response = coordinator_client.put(f"{BASE_URL}/api/certificates/font-settings", json=test_settings)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("Coordinator can save font settings")


class TestCertificatePreviewAPI:
    """Tests for certificate preview endpoint"""
    
    def test_preview_pdf_returns_png(self, admin_client):
        """POST /api/certificates/preview-pdf/{session_id}/{participant_id} - Returns PNG image"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/preview-pdf/{TEST_SESSION_ID}/{TEST_PARTICIPANT_ID}",
            json=None,
            timeout=60  # Preview can take 10-15 seconds due to LibreOffice conversion
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify response is PNG image
        content_type = response.headers.get("content-type", "")
        assert "image/png" in content_type, f"Expected PNG, got: {content_type}"
        
        # Verify image data is present
        assert len(response.content) > 1000, "PNG image too small, likely empty"
        print(f"Preview PNG generated: {len(response.content)} bytes")
    
    def test_preview_pdf_with_custom_settings(self, admin_client):
        """POST /api/certificates/preview-pdf - With custom font settings"""
        custom_settings = {
            "participant_name": {"font_size": 20, "max_lines": 1, "auto_fit": True, "bold": True},
            "top_margin": 70,
            "paragraph_spacing": 55
        }
        
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/preview-pdf/{TEST_SESSION_ID}/{TEST_PARTICIPANT_ID}",
            json=custom_settings,
            timeout=60
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        assert "image/png" in response.headers.get("content-type", "")
        print("Preview with custom settings generated successfully")
    
    def test_preview_pdf_invalid_session(self, admin_client):
        """POST /api/certificates/preview-pdf - Invalid session returns 404"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/preview-pdf/invalid-session-id/{TEST_PARTICIPANT_ID}",
            json=None,
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got: {response.status_code}"
        print("Invalid session correctly returns 404")
    
    def test_preview_pdf_invalid_participant(self, admin_client):
        """POST /api/certificates/preview-pdf - Invalid participant returns 404"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/preview-pdf/{TEST_SESSION_ID}/invalid-participant-id",
            json=None,
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got: {response.status_code}"
        print("Invalid participant correctly returns 404")


class TestCertificateGenerationAPI:
    """Tests for certificate PDF generation endpoints"""
    
    def test_generate_single_pdf_force(self, admin_client):
        """POST /api/certificates/generate-pdf/{session_id}/{participant_id}?force=true - Generates PDF"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/generate-pdf/{TEST_SESSION_ID}/{TEST_PARTICIPANT_ID}?force=true",
            timeout=60
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "certificate" in data
        
        cert = data["certificate"]
        assert "certificate_number" in cert
        assert "file_path" in cert
        assert "participant_id" in cert
        assert cert["participant_id"] == TEST_PARTICIPANT_ID
        
        # Verify certificate number format: MDDRC/COA/YYYY/MM/XXXXX
        cert_num = cert["certificate_number"]
        assert cert_num.startswith("MDDRC/COA/"), f"Invalid cert number format: {cert_num}"
        parts = cert_num.split("/")
        assert len(parts) == 5, f"Expected 5 parts in cert number: {cert_num}"
        assert parts[0] == "MDDRC"
        assert parts[1] == "COA"
        assert len(parts[2]) == 4  # Year
        assert len(parts[3]) == 2  # Month
        assert len(parts[4]) == 5  # Sequence number
        
        print(f"Certificate generated: {cert_num}")
        print(f"File path: {cert['file_path']}")
    
    def test_generate_single_pdf_without_force_checks_eligibility(self, admin_client):
        """POST /api/certificates/generate-pdf - Without force, checks eligibility"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/generate-pdf/{TEST_SESSION_ID}/{TEST_PARTICIPANT_ID}",
            timeout=60
        )
        # May return 200 if eligible, or 400 if not eligible
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 400:
            data = response.json()
            assert "detail" in data
            assert "not eligible" in data["detail"].lower() or "force=true" in data["detail"].lower()
            print(f"Eligibility check working: {data['detail']}")
        else:
            print("Participant is eligible, certificate generated")
    
    def test_generate_bulk_pdf_force(self, admin_client):
        """POST /api/certificates/generate-bulk-pdf/{session_id}?force=true - Bulk generates"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/generate-bulk-pdf/{TEST_SESSION_ID}?force=true",
            timeout=180  # Bulk generation can take longer
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "results" in data
        
        results = data["results"]
        assert "generated" in results
        assert "skipped" in results
        assert "errors" in results
        
        # Verify generated certificates have correct format
        for cert in results["generated"]:
            assert "participant_id" in cert
            assert "certificate_number" in cert
            cert_num = cert["certificate_number"]
            assert cert_num.startswith("MDDRC/COA/"), f"Invalid cert number: {cert_num}"
        
        print(f"Bulk generation: {len(results['generated'])} generated, {len(results['skipped'])} skipped, {len(results['errors'])} errors")
    
    def test_generate_bulk_pdf_invalid_session(self, admin_client):
        """POST /api/certificates/generate-bulk-pdf - Invalid session returns 404"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/generate-bulk-pdf/invalid-session-id?force=true",
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got: {response.status_code}"
        print("Invalid session correctly returns 404 for bulk generation")


class TestCertificateNumberFormat:
    """Tests specifically for certificate number format validation"""
    
    def test_certificate_number_format_current_month(self, admin_client):
        """Verify certificate number uses current year and month"""
        response = admin_client.post(
            f"{BASE_URL}/api/certificates/generate-pdf/{TEST_SESSION_ID}/{TEST_PARTICIPANT_ID}?force=true",
            timeout=60
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        cert = response.json()["certificate"]
        cert_num = cert["certificate_number"]
        
        # Parse certificate number
        parts = cert_num.split("/")
        cert_year = parts[2]
        cert_month = parts[3]
        
        # Verify it matches current date
        now = datetime.now()
        expected_year = now.strftime("%Y")
        expected_month = now.strftime("%m")
        
        assert cert_year == expected_year, f"Year mismatch: {cert_year} vs {expected_year}"
        assert cert_month == expected_month, f"Month mismatch: {cert_month} vs {expected_month}"
        print(f"Certificate number format verified: {cert_num}")


class TestAccessControl:
    """Tests for access control on certificate endpoints"""
    
    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests should be denied"""
        response = requests.get(f"{BASE_URL}/api/certificates/font-settings")
        # API returns 403 (Forbidden) for unauthenticated requests
        assert response.status_code in [401, 403], f"Expected 401/403, got: {response.status_code}"
        print("Unauthenticated access correctly denied")
    
    def test_coordinator_can_generate_certificates(self, coordinator_client):
        """Coordinator should be able to generate certificates"""
        response = coordinator_client.post(
            f"{BASE_URL}/api/certificates/generate-pdf/{TEST_SESSION_ID}/{TEST_PARTICIPANT_ID}?force=true",
            timeout=60
        )
        assert response.status_code == 200, f"Coordinator generation failed: {response.text}"
        print("Coordinator can generate certificates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
