import qrcode
import json
from typing import Dict, List
from datetime import datetime
import hashlib

class SignInService:
    def __init__(self):
        self.sign_in_records: Dict[str, List[dict]] = {}

    def generate_qr_code(self, activity_id: str) -> str:
        timestamp = datetime.now().timestamp()
        data = {
            'activity_id': activity_id,
            'timestamp': timestamp,
            'token': self._generate_token(activity_id, timestamp)
        }
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(data))
        return qr.make_image()

    def sign_in(self, activity_id: str, student_id: str) -> bool:
        try:
            if activity_id not in self.sign_in_records:
                self.sign_in_records[activity_id] = []
            
            # 检查是否重复签到
            if any(record['student_id'] == student_id for record in self.sign_in_records[activity_id]):
                return False
            
            self.sign_in_records[activity_id].append({
                'student_id': student_id,
                'timestamp': datetime.now().timestamp()
            })
            return True
        except Exception:
            return False

    def _generate_token(self, activity_id: str, timestamp: float) -> str:
        data = f"{activity_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()
