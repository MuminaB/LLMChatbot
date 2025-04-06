import mysql.connector
import os
from dotenv import load_dotenv

"""Database connection and new schema setup for RMU Chatbot"""

# Load environment variables
load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")  # Ensure DB_NAME is set to "rmu_chatbot"
    )

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Create Intents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Create Questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        intent_id INT DEFAULT NULL,
        question TEXT NOT NULL,
        category VARCHAR(100) DEFAULT NULL,
        version INT DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FULLTEXT(question)
    );
    """)

    # 2.1 Add foreign key constraint for intent_id **if it does not exist**
    cursor.execute("""
        SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
        WHERE TABLE_NAME = 'questions' AND COLUMN_NAME = 'intent_id';
    """)
    existing_fk = cursor.fetchone()
    if not existing_fk:
        try:
            cursor.execute("""
                ALTER TABLE questions 
                ADD CONSTRAINT fk_intent_id 
                FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE SET NULL;
            """)
        except Exception as e:
            print("❗ Warning: Failed to add fk_intent_id:", e)

    # 3. Create Answers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question_id INT NOT NULL,
        answer TEXT NOT NULL,
        version INT DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FULLTEXT(answer),
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
    );
    """)

    # 4. Create Synonyms table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS synonyms (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question_id INT NOT NULL,
        synonym TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FULLTEXT(synonym),
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
    );
    """)

    # 5. Create Conversation Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(100) NOT NULL,
        user_id INT DEFAULT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP NULL
    );
    """)

    # 6. Create Conversation Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(100) NOT NULL,
        sender ENUM('user', 'bot') NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FULLTEXT(message),
        INDEX(session_id)
    );
    """)

    # 7. Create User Profiles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        name VARCHAR(100),
        email VARCHAR(150),
        language VARCHAR(50) DEFAULT 'en',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """)

    # 8. Create Feedback table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INT AUTO_INCREMENT PRIMARY KEY,
        conversation_log_id INT,
        rating INT CHECK(rating BETWEEN 1 AND 5),
        comments TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_log_id) REFERENCES conversation_logs(id) ON DELETE CASCADE
    );
    """)

    # 9. Create Usage Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usage_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT DEFAULT NULL,
        session_id VARCHAR(100) DEFAULT NULL,
        event_type VARCHAR(50),
        event_description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ✅ Create indexes **only if they do not exist**
    cursor.execute("""
        SELECT INDEX_NAME FROM information_schema.STATISTICS 
        WHERE TABLE_NAME = 'questions' AND INDEX_NAME = 'idx_category';
    """)
    existing_index = cursor.fetchone()
    if not existing_index:
        try:
            cursor.execute("CREATE INDEX idx_category ON questions(category);")
        except Exception as e:
            print("❗ Warning: Failed to create idx_category:", e)

    cursor.execute("""
        SELECT INDEX_NAME FROM information_schema.STATISTICS 
        WHERE TABLE_NAME = 'questions' AND INDEX_NAME = 'idx_intent_id';
    """)
    existing_index = cursor.fetchone()
    if not existing_index:
        try:
            cursor.execute("CREATE INDEX idx_intent_id ON questions(intent_id);")
        except Exception as e:
            print("❗ Warning: Failed to create idx_intent_id:", e)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database schema setup completed successfully!")

# Run table creation when the module is imported
create_tables()
