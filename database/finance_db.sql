

CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    transaction_name VARCHAR(100) NOT NULL,
    type VARCHAR(10) CHECK (type IN ('Income', 'Expense')) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    notes TEXT,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);