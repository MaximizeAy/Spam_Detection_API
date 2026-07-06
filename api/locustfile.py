from locust import HttpUser, task, between
import random

# Expanded realistic samples for robust load testing
sample_messages = [
    "Congratulations! You won $5000.",
    "Meeting has been moved to tomorrow.",
    "Verify your account immediately.",
    "Claim your free iPhone now.",
    "DEAR BELOVED, I AM PRINCE ADAMU FROM NIGERIA. I HAVE $15,000,000 USD INHERITANCE THAT I NEED TO TRANSFER TO YOUR ACCOUNT URGENTLY. PLEASE SEND YOUR BANK DETAILS IMMEDIATELY. ACT NOW!!!",
    "GET 80% OFF on all medications!!! Viagra, Cialis, Xanax — no prescription needed! Order now at www.cheap-pills.biz.",
    "Hi team, just a reminder about our Q4 planning meeting tomorrow at 2pm in Conference Room B. Please review the attached agenda.",
    "URGENT: Your Bitcoin wallet has been selected for our EXCLUSIVE doubling program! Send 0.5 BTC and receive 1.0 BTC back in 24 hours GUARANTEED!!!",
    "This week in design: We explore the evolution of brutalist web interfaces and interview three leading studios about their approach to typography.",
    "Click here to verify your bank account details immediately to prevent suspension: http://secure-bank-verify.xyz/login",
]

class SpamLensUser(HttpUser):
    # Target the local FastAPI server
    host = "http://localhost:8000"
    
    # Simulate a user thinking/reading for 1 to 3 seconds between requests
    wait_time = between(1, 3)

    @task(3)  # Weight 3: Single analysis is the most common action
    def analyze_single(self):
        message = random.choice(sample_messages)
        
        with self.client.post("/analyze", json={"text": message}, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                # Optional: Log to console during test to see what Locust is doing
                # print(f"[{data['final_verdict'].upper()}] {message[:50]}... -> {data['final_confidence']}%")
                pass
            else:
                response.failure(f"Failed with status {response.status_code}: {response.text}")

    @task(1)  # Weight 1: Batch upload happens less frequently
    def analyze_batch(self):
        # Pick between 2 and 5 random emails for the batch payload
        batch_size = random.randint(2, 5)
        messages = random.sample(sample_messages, batch_size)
        
        with self.client.post("/analyze/batch", json={"texts": messages}, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Batch failed with status {response.status_code}: {response.text}")