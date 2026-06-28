from dotenv import load_dotenv
import os

load_dotenv()


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_only_change_me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))