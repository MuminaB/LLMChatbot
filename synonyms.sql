USE rmu_chatbot;

-- Sample for "How can I apply to RMU?"
INSERT INTO synonyms (question_id, synonym)
SELECT id, 'how to register at RMU' FROM questions WHERE question = 'How can I apply to RMU?';

INSERT INTO synonyms (question_id, synonym)
SELECT id, 'RMU admission process' FROM questions WHERE question = 'How can I apply to RMU?';

-- Another example
INSERT INTO synonyms (question_id, synonym)
SELECT id, 'available programs' FROM questions WHERE question = 'What courses are offered';
