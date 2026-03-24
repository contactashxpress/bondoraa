from datetime import date, timedelta

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from accounts.models import User
from signups.models import CreditDemand


def _minimal_pdf(name: str) -> SimpleUploadedFile:
    content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    return SimpleUploadedFile(name, content, content_type="application/pdf")


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
        # Fichiers dans le même dict que les champs (multipart) — requis pour Client.post
        data["id_recto"] = _minimal_pdf("id_recto.pdf")
        data["revenus"] = _minimal_pdf("revenus.pdf")
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
        self.assertGreater(demande.step_statuses.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn(ref, mail.outbox[0].body)
