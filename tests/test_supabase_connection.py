from src.config import supabase


def test_supabase_connection():
    try:
        supabase.auth.get_session()
        print("Connection Successful!")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_supabase_connection()
