-- ====================================================
-- 1. Create the Database and Use It
-- ====================================================
CREATE DATABASE IF NOT EXISTS rmu_chatbot;
USE rmu_chatbot;

-- ====================================================
-- 2. Create Tables
-- ====================================================

-- 2.1 Intents Table: Groups related questions by underlying intent.
CREATE TABLE IF NOT EXISTS intents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2.2 Questions Table: Stores the questions with optional intent reference and versioning.
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

ALTER TABLE questions 
    ADD CONSTRAINT fk_intent_id 
    FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE SET NULL;

-- 2.3 Answers Table: Stores answers linked to questions.
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

-- 2.4 Synonyms Table: For alternate phrasings linked to a canonical question.
CREATE TABLE IF NOT EXISTS synonyms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    synonym TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FULLTEXT(synonym),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- 2.5 Conversation Sessions: For managing user sessions.
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id INT DEFAULT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL
);

-- 2.6 Conversation Logs: For storing each message in a session.
CREATE TABLE IF NOT EXISTS conversation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    sender ENUM('user', 'bot') NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FULLTEXT(message),
    INDEX(session_id)
);

-- 2.7 User Profiles: For personalization.
CREATE TABLE IF NOT EXISTS user_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    name VARCHAR(100),
    email VARCHAR(150),
    language VARCHAR(50) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2.8 Feedback: To capture user ratings and comments.
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_log_id INT,
    rating INT CHECK(rating BETWEEN 1 AND 5),
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_log_id) REFERENCES conversation_logs(id) ON DELETE CASCADE
);

-- 2.9 Usage Logs: For analytics and tracking.
CREATE TABLE IF NOT EXISTS usage_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL,
    session_id VARCHAR(100) DEFAULT NULL,
    event_type VARCHAR(50),
    event_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional indexes for frequently queried columns.
CREATE INDEX idx_category ON questions(category);
CREATE INDEX idx_intent_id ON questions(intent_id);

-- ====================================================
-- 3. Insert Data into the New Schema
-- ====================================================

-- 3.1 Insert Intents
INSERT INTO intents (name, description) VALUES
('greeting', 'Handles greeting messages and basic pleasantries'),
('admissions', 'Handles questions related to admissions'),
('academics', 'Handles academic information and department details'),
('administration', 'Handles administrative and official information'),
('location', 'Handles location-based queries'),
('contact', 'Handles contact information queries'),
('campus', 'Handles campus facility queries'),
('housing', 'Handles questions about hostel and accommodation'),
('finance', 'Handles financial queries such as fees'),
('scholarships', 'Handles scholarship-related queries'),
('registration', 'Handles course registration queries'),
('introduction', 'Handles self-identification queries'),
('gratitude', 'Handles expressions of thanks'),
('farewell', 'Handles closing and goodbye messages');

-- 3.2 Insert Questions, Answers, and Synonyms

-- --- GREETING ---
-- Canonical: "Hello"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'greeting' LIMIT 1), 'Hello', 'greeting', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Hello' LIMIT 1), 'Hello! How can I assist you today?', 1);
INSERT INTO synonyms (question_id, synonym)
VALUES 
((SELECT id FROM questions WHERE question = 'Hello' LIMIT 1), 'Hi'),
((SELECT id FROM questions WHERE question = 'Hello' LIMIT 1), 'Hey');

-- "Good morning"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'greeting' LIMIT 1), 'Good morning', 'greeting', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Good morning' LIMIT 1), 'Good morning! How may I help you?', 1);

-- "Good afternoon"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'greeting' LIMIT 1), 'Good afternoon', 'greeting', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Good afternoon' LIMIT 1), 'Good afternoon! What can I do for you?', 1);

-- "Good evening"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'greeting' LIMIT 1), 'Good evening', 'greeting', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Good evening' LIMIT 1), 'Good evening! How can I assist you?', 1);

-- "What's up?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'greeting' LIMIT 1), 'What''s up?', 'greeting', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What''s up?' LIMIT 1), 'Not much! Just here to help. What do you need assistance with?', 1);

-- "How are you?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'greeting' LIMIT 1), 'How are you?', 'greeting', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'How are you?' LIMIT 1), 'I''m just a chatbot, but I''m here and ready to help!', 1);

-- --- INTRODUCTION ---
-- "Who are you?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'introduction' LIMIT 1), 'Who are you?', 'introduction', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Who are you?' LIMIT 1), 'I''m RMU''s virtual assistant, here to answer your university-related questions!', 1);

-- "Can you help me?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'introduction' LIMIT 1), 'Can you help me?', 'introduction', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Can you help me?' LIMIT 1), 'Of course! Let me know what you need help with.', 1);

-- --- GRATITUDE ---
-- "Thank you"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'gratitude' LIMIT 1), 'Thank you', 'gratitude', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Thank you' LIMIT 1), 'You''re welcome! Let me know if you need anything else.', 1);
INSERT INTO synonyms (question_id, synonym)
VALUES ((SELECT id FROM questions WHERE question = 'Thank you' LIMIT 1), 'Thanks');

-- --- FAREWELL ---
-- "Bye"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'farewell' LIMIT 1), 'Bye', 'farewell', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Bye' LIMIT 1), 'Goodbye! Have a great day!', 1);

-- "See you later"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'farewell' LIMIT 1), 'See you later', 'farewell', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'See you later' LIMIT 1), 'See you later! Don''t hesitate to ask if you need help again.', 1);

-- --- ADMISSIONS ---
-- "How can I apply to RMU?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'admissions' LIMIT 1), 'How can I apply to RMU?', 'admissions', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'How can I apply to RMU?' LIMIT 1), 'To apply to RMU, visit our Online Admissions Portal. Ensure you''ve read and understood the admissions requirements before logging in.', 1);

-- "What are the application fees for international applicants?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'admissions' LIMIT 1), 'What are the application fees for international applicants?', 'admissions', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What are the application fees for international applicants?' LIMIT 1), 'The processing fees for international applicants are: Masters/Upgraders programmes - $70.00, BSc. programmes - $50.00, Diploma/MEM programmes - $40.00.', 1);

-- "How can I track my application status?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'admissions' LIMIT 1), 'How can I track my application status?', 'admissions', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'How can I track my application status?' LIMIT 1), 'You can track your application status through the RMU Admissions Portal using your applicant login details.', 1);

-- --- ACADEMICS ---
-- "Where can I find the short courses timetable?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'academics' LIMIT 1), 'Where can I find the short courses timetable?', 'academics', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Where can I find the short courses timetable?' LIMIT 1), 'The short courses timetable is available on our website. You can view it here.', 1);

-- "What is the grading scale used at RMU?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'academics' LIMIT 1), 'What is the grading scale used at RMU?', 'academics', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What is the grading scale used at RMU?' LIMIT 1), 'RMU''s grading scale is as follows: A+ (80-100) - Outstanding, A (70-79) - Excellent, A- (65-69) - Very Good, B+ (60-64) - Good, B (55-59) - Above Average, B- (50-54) - Average, C+ (45-49) - Pass, C (40-44) - Pass, D (30-39) - Fail, F (0-29) - Fail.', 1);

-- "What constitutes a pass grade at RMU?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'academics' LIMIT 1), 'What constitutes a pass grade at RMU?', 'academics', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What constitutes a pass grade at RMU?' LIMIT 1), 'A pass grade is a grade of C or above.', 1);

-- "Where can I find the academic calendar?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'academics' LIMIT 1), 'Where can I find the academic calendar?', 'academics', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Where can I find the academic calendar?' LIMIT 1), 'The academic calendar is available on the RMU website under the ''Academics'' section.', 1);

-- "What departments are available at RMU?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'academics' LIMIT 1), 'What departments are available at RMU?', 'academics', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What departments are available at RMU?' LIMIT 1), 'RMU has departments such as Marine Engineering, Nautical Studies, Maritime Law, and Logistics.', 1);

-- --- ADMINISTRATION ---
-- "Who is the Vice Chancellor of RMU?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'administration' LIMIT 1), 'Who is the Vice Chancellor of RMU?', 'administration', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Who is the Vice Chancellor of RMU?' LIMIT 1), 'Currently, RMU has an acting vice chancellor by the name Dr. Jethro W. Brooks Jnr.', 1);

-- "How can I contact the University Registrar?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'administration' LIMIT 1), 'How can I contact the University Registrar?', 'administration', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'How can I contact the University Registrar?' LIMIT 1), 'You can reach the University Registrar via email at registrar@rmu.edu.gh or by phone at +233 302 714070.', 1);

-- "What is the office number for the Registrar?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'administration' LIMIT 1), 'What is the office number for the Registrar?', 'administration', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What is the office number for the Registrar?' LIMIT 1), 'You can reach the Registrar at +233 302 714070.', 1);

-- --- LOCATION ---
-- "Where is RMU located?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'location' LIMIT 1), 'Where is RMU located?', 'location', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Where is RMU located?' LIMIT 1), 'RMU is located at P.O.BOX GP1115, Nungua, Accra – Ghana, West Africa.', 1);

-- --- CONTACT ---
-- "What are the contact numbers for RMU?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'contact' LIMIT 1), 'What are the contact numbers for RMU?', 'contact', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What are the contact numbers for RMU?' LIMIT 1), 'You can contact RMU at +233 302 712775, +233 302 718225, or +233 302 714070.', 1);

-- --- CAMPUS ---
-- "Where is the cadet shop located?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'campus' LIMIT 1), 'Where is the cadet shop located?', 'campus', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'Where is the cadet shop located?' LIMIT 1), 'The cadet shop is located on the main campus near the administration block.', 1);

-- --- HOUSING ---
-- "How do I apply for hostel accommodation?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'housing' LIMIT 1), 'How do I apply for hostel accommodation?', 'housing', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'How do I apply for hostel accommodation?' LIMIT 1), 'Visit the Hostel Office on campus or check the RMU website for the application process.', 1);

-- --- FINANCE ---
-- "What are the tuition fees for the academic year?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'finance' LIMIT 1), 'What are the tuition fees for the academic year?', 'finance', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What are the tuition fees for the academic year?' LIMIT 1), 'Tuition fees vary by department. Please refer to the RMU Fees section on the website.', 1);

-- --- SCHOLARSHIPS ---
-- "What scholarships does RMU offer?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'scholarships' LIMIT 1), 'What scholarships does RMU offer?', 'scholarships', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'What scholarships does RMU offer?' LIMIT 1), 'RMU offers merit-based and need-based scholarships. Visit the Scholarships page on the RMU website for details.', 1);

-- --- REGISTRATION ---
-- "How do I register for courses?"
INSERT INTO questions (intent_id, question, category, version)
VALUES ((SELECT id FROM intents WHERE name = 'registration' LIMIT 1), 'How do I register for courses?', 'registration', 1);
INSERT INTO answers (question_id, answer, version)
VALUES ((SELECT id FROM questions WHERE question = 'How do I register for courses?' LIMIT 1), 'Course registration is done online via the RMU Student Portal.', 1);
