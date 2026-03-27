import io
from datetime import date, timedelta
from unittest import skipUnless

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from accounts.models import User
from config.file_validation import DOCUMENT_PRESET, MAGIC_AVAILABLE
from config.secure_upload import process_demand_upload
from signups.models import CreditDemand


def _valid_pdf_bytes() -> bytes:
    from pypdf import PdfWriter

    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    w.write(buf)
    return buf.getvalue()


def _minimal_jpeg_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(128, 64, 32)).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _minimal_png_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), color=(10, 20, 30, 255)).save(buf, format="PNG")
    return buf.getvalue()


class DemandeCreditSansSignatureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="demande-test@example.com",
            password="SecretPass123!",
            email_verified=True,
        )
        self.client = Client()

    def test_soumission_demande_sans_champ_signature_reussit(self):
        self.client.force_login(self.user)
        birth = date.today() - timedelta(days=365 * 25)
        data = {
            "montant": "5000",
            "duree": "48",
            "prenom": "Jean",
            "nom": "Test",
            "naissance": birth.isoformat(),
            "nationalite": "FR",
            "email": "demande-test@example.com",
            "tel": "0612345678",
            "code_postal": "75001",
            "adresse": "1 rue Test",
            "famille": "celibataire",
            "emploi": "cdi",
            "revenus": "3000",
            "autres_revenus": "0",
            "charges": "500",
            "logement": "locataire",
            "motif": "travaux",
            "type_id": "cni",
            "cgu": "on",
            "exacts": "on",
            "marketing": "",
        }
        data["id_recto"] = SimpleUploadedFile(
            "id_recto.pdf",
            _valid_pdf_bytes(),
            content_type="application/pdf",
        )
        data["revenus"] = SimpleUploadedFile(
            "revenus.pdf",
            _valid_pdf_bytes(),
            content_type="application/pdf",
        )
        resp = self.client.post(
            "/demande/",
            data=data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_HOST="bondoraa.com",
        )
        self.assertEqual(resp.status_code, 201)
        payload = resp.json()
        self.assertTrue(payload.get("success"))
        self.assertIn("reference", payload)
        ref = payload["reference"]
        demande = CreditDemand.objects.get(reference=ref)
        self.assertEqual(demande.user, self.user)
        self.assertEqual(demande.documents.count(), 2)
        for doc in demande.documents.all():
            base = doc.fichier.name.split("/")[-1]
            self.assertRegex(
                base,
                r"^(id_recto|revenus)_[a-f0-9]{32}\.pdf$",
            )
        self.assertGreater(demande.step_statuses.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn(ref, mail.outbox[0].body)


class SecureDemandUploadTest(TestCase):
    def test_jpeg_reencode_ok(self):
        raw = _minimal_jpeg_bytes()
        up = SimpleUploadedFile("doc.jpg", raw, content_type="image/jpeg")
        cf, err = process_demand_upload(up, DOCUMENT_PRESET, "doc")
        self.assertIsNone(err)
        self.assertIsNotNone(cf)
        assert cf is not None
        self.assertTrue(cf.name.endswith(".jpg"))
        self.assertGreater(len(cf.read()), 0)

    def test_png_reencode_ok(self):
        raw = _minimal_png_bytes()
        up = SimpleUploadedFile("doc.png", raw, content_type="image/png")
        cf, err = process_demand_upload(up, DOCUMENT_PRESET, "doc")
        self.assertIsNone(err)
        self.assertIsNotNone(cf)
        assert cf is not None
        self.assertTrue(cf.name.endswith(".png"))

    def test_pdf_valide_ok(self):
        raw = _valid_pdf_bytes()
        up = SimpleUploadedFile("x.pdf", raw, content_type="application/pdf")
        cf, err = process_demand_upload(up, DOCUMENT_PRESET, "doc")
        self.assertIsNone(err)
        self.assertIsNotNone(cf)
        assert cf is not None
        self.assertTrue(cf.name.endswith(".pdf"))

    def test_pdf_header_seulement_rejete(self):
        bad = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        up = SimpleUploadedFile("x.pdf", bad, content_type="application/pdf")
        cf, err = process_demand_upload(up, DOCUMENT_PRESET, "doc")
        self.assertIsNotNone(err)
        self.assertIsNone(cf)

    def test_extension_masquee_rejetee_si_magic(self):
        raw = b"<!DOCTYPE html><script>alert(1)</script>"
        up = SimpleUploadedFile("fake.jpg", raw, content_type="image/jpeg")
        cf, err = process_demand_upload(up, DOCUMENT_PRESET, "doc")
        if MAGIC_AVAILABLE:
            self.assertIsNotNone(err)
            self.assertIsNone(cf)
        else:
            # Sans magic : rejet à l’ouverture PIL
            self.assertIsNotNone(err)
            self.assertIsNone(cf)

    @skipUnless(MAGIC_AVAILABLE, "python-magic / libmagic requis")
    @override_settings(FILE_VALIDATION_REQUIRE_MAGIC=True)
    def test_exige_magic_si_parametre(self):
        # N’importe quel contenu avec bonne extension mais mauvais magic
        up = SimpleUploadedFile("x.pdf", b"not a pdf", content_type="application/pdf")
        cf, err = process_demand_upload(up, DOCUMENT_PRESET, "doc")
        self.assertIsNotNone(err)
        self.assertIsNone(cf)
