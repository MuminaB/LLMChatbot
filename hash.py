from werkzeug.security import generate_password_hash

# This uses pbkdf2:sha256, which is compatible
print(generate_password_hash("admin123", method='pbkdf2:sha256'))
