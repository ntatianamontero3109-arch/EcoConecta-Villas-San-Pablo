import unittest
from app.chatbot import answer_question

class EcoBotTests(unittest.TestCase):
    def test_request_creation(self):
        result = answer_question("¿Cómo puedo pedir que recojan mis residuos?")
        self.assertEqual(result["category"], "solicitud")
        self.assertIn("inicia sesión", result["answer"])

    def test_plastic(self):
        result = answer_question("¿Qué hago con las botellas plásticas?")
        self.assertEqual(result["category"], "plasticos")
        self.assertIn("limpios y secos", result["answer"])

    def test_batteries(self):
        self.assertEqual(answer_question("¿Qué hago con pilas usadas?")["category"], "pilas")

    def test_tracking_phrasings(self):
        questions = [
            "¿Cómo consulto mi solicitud?",
            "¿Dónde veo mi solicitud?",
            "¿Cómo reviso el estado de mi recolección?",
            "¿Ya recogieron mis residuos?",
            "¿Cómo va mi pedido?",
            "¿Dónde consulto el código de seguimiento?",
            "¿Qué pasó con mi solicitud?",
        ]
        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(answer_question(question)["category"], "seguimiento")

    def test_schedule_is_not_tracking(self):
        for question in ["¿A qué hora pasa el recolector?", "¿Qué días recogen residuos?"]:
            with self.subTest(question=question):
                self.assertEqual(answer_question(question)["category"], "horarios")


    def test_missed_pickup_is_delay(self):
        questions = [
            "¿Qué pasa si no vienen a recoger mis residuos?",
            "No llegaron el día programado",
            "El recolector no vino",
            "¿Qué hago si no han recogido mi solicitud?",
        ]
        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(answer_question(question)["category"], "retraso")

    def test_supported_materials_question(self):
        result = answer_question("¿Qué residuos recibe EcoConecta?")
        self.assertEqual(result["category"], "tipos")

    def test_follow_up_context(self):
        history = [
            {"role": "user", "content": "¿Cómo solicito una recolección?"},
            {"role": "assistant", "content": "Inicia sesión y abre Solicitar recolección."},
            {"role": "user", "content": "¿Y después qué hago?"},
        ]
        result = answer_question(history[-1]["content"], history)
        self.assertEqual(result["category"], "solicitud")

    def test_unknown_does_not_invent(self):
        result = answer_question("¿A qué hora exacta pasa mañana el camión por mi calle?")
        self.assertTrue(result["answer"])
        self.assertIn(result["category"], {"horarios", "sin_coincidencia"})

    def test_no_external_ai_required(self):
        self.assertEqual(answer_question("¿Qué es EcoConecta?")["category"], "que_es")

if __name__ == "__main__":
    unittest.main()
