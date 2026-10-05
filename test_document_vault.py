"""
=============================================================
Student Document Vault Test Suite
Validates security, user ownership isolation, file validation,
premium entitlement enforcement, and CRUD operations.
=============================================================
"""

import io
import os
import unittest
from app import app, VAULT_STORAGE_DIR, MAX_DOCUMENT_SIZE
from models.database import (
    init_auth_db,
    get_connection,
    create_user,
    set_user_premium_status,
    get_user_documents,
    get_user_document_by_id,
    delete_user_document
)

class StudentDocumentVaultTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_auth_db()
        conn = get_connection()
        cursor = conn.cursor()
        
        # Clean up test users if existing
        cursor.execute("DELETE FROM student_documents")
        cursor.execute("DELETE FROM users WHERE email IN ('vault_free@test.com', 'vault_prem_a@test.com', 'vault_prem_b@test.com')")
        conn.commit()
        conn.close()

        # 1. Free User
        cls.free_user_id = create_user("Free Vault User", "vault_free@test.com", "hash_free")
        set_user_premium_status(cls.free_user_id, False)

        # 2. Premium User A
        cls.prem_user_a_id = create_user("Premium User A", "vault_prem_a@test.com", "hash_prem_a")
        set_user_premium_status(cls.prem_user_a_id, True)

        # 3. Premium User B
        cls.prem_user_b_id = create_user("Premium User B", "vault_prem_b@test.com", "hash_prem_b")
        set_user_premium_status(cls.prem_user_b_id, True)

        cls.client = app.test_client()

    def setUp(self):
        # Clean up documents table before each test
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM student_documents")
        conn.commit()
        conn.close()

    def _login_session(self, user_id, user_name, is_premium):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = user_name
            sess["is_premium"] = 1 if is_premium else 0

    # -------------------------------------------------------------
    # 1. ACCESS CONTROL TESTS
    # -------------------------------------------------------------

    def test_01_unauthenticated_access_blocked(self):
        """Unauthenticated user cannot access vault APIs or counselling view."""
        with self.client.session_transaction() as sess:
            sess.clear()

        # Counselling page redirects to login
        res_view = self.client.get("/counselling")
        self.assertEqual(res_view.status_code, 302)
        self.assertIn("/login", res_view.headers.get("Location", ""))

        # Vault document API returns 401 or redirect
        res_api = self.client.get("/api/vault/documents")
        self.assertIn(res_api.status_code, [401, 302])

    def test_02_free_user_blocked_from_counselling_and_vault_apis(self):
        """Free user visiting counselling or vault APIs is blocked/redirected to premium."""
        self._login_session(self.free_user_id, "Free Vault User", is_premium=False)

        # Visiting counselling redirects to /premium
        res_view = self.client.get("/counselling")
        self.assertEqual(res_view.status_code, 302)
        self.assertIn("/premium", res_view.headers.get("Location", ""))

        # Vault GET API returns 403 Forbidden
        res_api = self.client.get("/api/vault/documents")
        self.assertEqual(res_api.status_code, 403)
        self.assertEqual(res_api.get_json()["status"], "premium_required")

        # Vault Upload API returns 403 Forbidden
        res_upload = self.client.post("/api/vault/upload", data={"document_type": "10th Marksheet"})
        self.assertEqual(res_upload.status_code, 403)

    def test_03_premium_user_can_access_counselling_vault_view(self):
        """Premium user can load counselling page with vault section rendered."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)
        res = self.client.get("/counselling")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("My Documents &amp; Certificate Vault", html)
        self.assertIn("10th Marksheet / SSLC", html)
        self.assertIn("vault-section", html)

    # -------------------------------------------------------------
    # 2. UPLOAD & VALIDATION TESTS
    # -------------------------------------------------------------

    def test_04_upload_valid_pdf_document(self):
        """Premium user can upload a valid PDF document with genuine magic bytes."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        data = {
            "document_type": "10th Marksheet",
            "file": (io.BytesIO(valid_pdf_content), "my_10th_marksheet.pdf")
        }

        res = self.client.post("/api/vault/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertEqual(json_data["status"], "success")
        self.assertEqual(json_data["document"]["document_type"], "10th Marksheet")
        self.assertEqual(json_data["document"]["mime_type"], "application/pdf")
        self.assertEqual(json_data["document"]["original_filename"], "my_10th_marksheet.pdf")

    def test_05_upload_valid_image_document(self):
        """Premium user can upload valid JPEG / PNG documents."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        # JPEG signature \xff\xd8\xff
        valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00"
        data = {
            "document_type": "+2 Marksheet",
            "file": (io.BytesIO(valid_jpeg), "hsc_marksheet.jpg")
        }
        res = self.client.post("/api/vault/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["document"]["mime_type"], "image/jpeg")

    def test_06_reject_invalid_file_extension(self):
        """Executable or dangerous script extensions (.exe, .sh, .py, .js) are rejected."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        for bad_name in ["malicious.exe", "script.sh", "payload.py", "app.js", "page.html"]:
            data = {
                "document_type": "10th Marksheet",
                "file": (io.BytesIO(b"fake payload content"), bad_name)
            }
            res = self.client.post("/api/vault/upload", data=data, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 400)
            self.assertIn("not allowed", res.get_json()["message"].lower())

    def test_07_reject_mismatched_magic_bytes(self):
        """A file disguised as .pdf with non-PDF content is rejected for security."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        fake_pdf = b"This is plain text with no PDF header bytes"
        data = {
            "document_type": "Transfer Certificate",
            "file": (io.BytesIO(fake_pdf), "fake_doc.pdf")
        }
        res = self.client.post("/api/vault/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("do not match", res.get_json()["message"].lower())

    def test_08_reject_invalid_category(self):
        """Invalid document category returns 400 Bad Request."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        valid_pdf_content = b"%PDF-1.4\n%%EOF"
        data = {
            "document_type": "Arbitrary Unknown Category",
            "file": (io.BytesIO(valid_pdf_content), "test.pdf")
        }
        res = self.client.post("/api/vault/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalid document category", res.get_json()["message"].lower())

    def test_09_reject_oversized_file(self):
        """File larger than MAX_DOCUMENT_SIZE (10MB) is rejected."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        # 11 MB fake stream
        large_content = b"%PDF-1.4\n" + (b"0" * (MAX_DOCUMENT_SIZE + 1024))
        data = {
            "document_type": "Community Certificate",
            "file": (io.BytesIO(large_content), "huge_cert.pdf")
        }
        res = self.client.post("/api/vault/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("exceeds", res.get_json()["message"].lower())

    # -------------------------------------------------------------
    # 3. USER ISOLATION & IDOR PREVENTION TESTS
    # -------------------------------------------------------------

    def test_10_strict_user_document_isolation(self):
        """User A and User B cannot view, download, or list each other's documents."""
        # Step 1: User A uploads 10th marksheet
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)
        pdf_a = b"%PDF-1.4\nUser A Marksheet Content\n%%EOF"
        res_a_upload = self.client.post("/api/vault/upload", data={
            "document_type": "10th Marksheet",
            "file": (io.BytesIO(pdf_a), "user_a_10th.pdf")
        }, content_type="multipart/form-data")
        self.assertEqual(res_a_upload.status_code, 200)
        doc_a_id = res_a_upload.get_json()["document"]["id"]

        # Step 2: User B uploads Community Certificate
        self._login_session(self.prem_user_b_id, "Premium User B", is_premium=True)
        pdf_b = b"%PDF-1.4\nUser B Community Certificate\n%%EOF"
        res_b_upload = self.client.post("/api/vault/upload", data={
            "document_type": "Community Certificate",
            "file": (io.BytesIO(pdf_b), "user_b_community.pdf")
        }, content_type="multipart/form-data")
        self.assertEqual(res_b_upload.status_code, 200)
        doc_b_id = res_b_upload.get_json()["document"]["id"]

        # Step 3: User B lists documents -> sees only User B's document
        res_b_list = self.client.get("/api/vault/documents")
        self.assertEqual(res_b_list.status_code, 200)
        b_docs = res_b_list.get_json()["documents"]
        self.assertEqual(len(b_docs), 1)
        self.assertEqual(b_docs[0]["id"], doc_b_id)
        self.assertEqual(b_docs[0]["original_filename"], "user_b_community.pdf")

        # Step 4: User B tries to view/download User A's document (IDOR attempt) -> Blocked (404/403)
        res_idor_view = self.client.get(f"/api/vault/document/{doc_a_id}/view")
        self.assertEqual(res_idor_view.status_code, 404)

        res_idor_dl = self.client.get(f"/api/vault/document/{doc_a_id}/download")
        self.assertEqual(res_idor_dl.status_code, 404)

        # Step 5: User B tries to delete User A's document -> Blocked (404/403)
        res_idor_del = self.client.delete(f"/api/vault/document/{doc_a_id}")
        self.assertEqual(res_idor_del.status_code, 404)

        # Step 6: Verify User A's document is still intact
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)
        res_a_view = self.client.get(f"/api/vault/document/{doc_a_id}/view")
        self.assertEqual(res_a_view.status_code, 200)
        self.assertEqual(res_a_view.data, pdf_a)

    # -------------------------------------------------------------
    # 4. REPLACE & DELETE LIFECYCLE TESTS
    # -------------------------------------------------------------

    def test_11_replace_document_updates_db_and_disk(self):
        """Uploading the same document category replaces the existing file and removes old file from disk."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        # 1. Initial upload
        pdf_v1 = b"%PDF-1.4\nVersion 1 Content\n%%EOF"
        res_v1 = self.client.post("/api/vault/upload", data={
            "document_type": "+1 Marksheet",
            "file": (io.BytesIO(pdf_v1), "marksheet_v1.pdf")
        }, content_type="multipart/form-data")
        self.assertEqual(res_v1.status_code, 200)
        doc_id_1 = res_v1.get_json()["document"]["id"]

        # Fetch DB record to check storage filename
        doc_record_1 = get_user_document_by_id(self.prem_user_a_id, doc_id_1)
        old_file_path = os.path.join(VAULT_STORAGE_DIR, doc_record_1["storage_key"])
        self.assertTrue(os.path.exists(old_file_path))

        # 2. Replace with Version 2
        pdf_v2 = b"%PDF-1.4\nVersion 2 Content Replacement\n%%EOF"
        res_v2 = self.client.post("/api/vault/upload", data={
            "document_type": "+1 Marksheet",
            "file": (io.BytesIO(pdf_v2), "marksheet_v2_updated.pdf")
        }, content_type="multipart/form-data")
        self.assertEqual(res_v2.status_code, 200)
        doc_id_2 = res_v2.get_json()["document"]["id"]

        # Replaced row has same ID or updated metadata
        self.assertEqual(doc_id_1, doc_id_2)
        doc_record_2 = get_user_document_by_id(self.prem_user_a_id, doc_id_2)
        self.assertEqual(doc_record_2["original_filename"], "marksheet_v2_updated.pdf")

        # Verify old file removed and new file exists
        new_file_path = os.path.join(VAULT_STORAGE_DIR, doc_record_2["storage_key"])
        self.assertTrue(os.path.exists(new_file_path))
        if old_file_path != new_file_path:
            self.assertFalse(os.path.exists(old_file_path))

        # Verify download returns version 2 content
        res_dl = self.client.get(f"/api/vault/document/{doc_id_2}/download")
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl.data, pdf_v2)

    def test_12_delete_document_removes_db_and_disk(self):
        """Deleting a document removes the database entry and cleans up the stored file."""
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)

        # Upload document
        pdf_tc = b"%PDF-1.4\nTransfer Certificate Content\n%%EOF"
        res_upload = self.client.post("/api/vault/upload", data={
            "document_type": "Transfer Certificate",
            "file": (io.BytesIO(pdf_tc), "tc_doc.pdf")
        }, content_type="multipart/form-data")
        doc_id = res_upload.get_json()["document"]["id"]

        doc_record = get_user_document_by_id(self.prem_user_a_id, doc_id)
        file_path = os.path.join(VAULT_STORAGE_DIR, doc_record["storage_key"])
        self.assertTrue(os.path.exists(file_path))

        # Delete document via DELETE method
        res_del = self.client.delete(f"/api/vault/document/{doc_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.get_json()["status"], "success")

        # Verify DB entry is gone
        self.assertIsNone(get_user_document_by_id(self.prem_user_a_id, doc_id))

        # Verify file on disk is removed
        self.assertFalse(os.path.exists(file_path))

        # Verify subsequent view returns 404
        res_view = self.client.get(f"/api/vault/document/{doc_id}/view")
        self.assertEqual(res_view.status_code, 404)

    def test_13_relogin_preserves_vault_documents(self):
        """User documents remain accessible and isolated across logout / login sessions."""
        # 1. Login A and upload
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)
        pdf_data = b"%PDF-1.4\nPersisted Session Document\n%%EOF"
        res_upload = self.client.post("/api/vault/upload", data={
            "document_type": "Income Certificate",
            "file": (io.BytesIO(pdf_data), "income_cert.pdf")
        }, content_type="multipart/form-data")
        doc_id = res_upload.get_json()["document"]["id"]

        # 2. Logout
        self.client.get("/logout")

        # 3. Relogin as User A
        self._login_session(self.prem_user_a_id, "Premium User A", is_premium=True)
        res_docs = self.client.get("/api/vault/documents")
        self.assertEqual(res_docs.status_code, 200)
        docs = res_docs.get_json()["documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["id"], doc_id)
        self.assertEqual(docs[0]["document_type"], "Income Certificate")


if __name__ == "__main__":
    unittest.main()
