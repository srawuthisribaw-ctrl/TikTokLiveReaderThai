import unittest
from core.licensing import verify_key
from key_generator import generate_key

class TestLicensing(unittest.TestCase):
    def test_key_verification_success(self):
        machine_id = "test-machine-id-12345"
        key = generate_key(machine_id)
        self.assertTrue(verify_key(machine_id, key))

    def test_key_verification_failure_with_wrong_id(self):
        machine_id1 = "machine-1"
        machine_id2 = "machine-2"
        key1 = generate_key(machine_id1)
        self.assertFalse(verify_key(machine_id2, key1))

    def test_key_verification_failure_with_invalid_key(self):
        self.assertFalse(verify_key("machine-1", "invalid_base64_or_signature"))
