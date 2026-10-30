CREATE DATABASE IF NOT EXISTS bristol_pulse_v2;
USE bristol_pulse_v2;

CREATE TABLE User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_student BOOLEAN,
    user_type VARCHAR(20), -- 'standard', 'admin'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE Venue (
    venue_id INT AUTO_INCREMENT PRIMARY KEY,
    venue_name VARCHAR(100),
    address VARCHAR(255),
    capacity INT,
    suitability_notes VARCHAR(255)
);
CREATE TABLE EventCategory (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50),
    category_description VARCHAR(255)
);
CREATE TABLE Event (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    venue_id INT NOT NULL,
    category_id INT NOT NULL,
    event_name VARCHAR(150),
    event_description TEXT,
    booking_deadline DATETIME,
    created_by_user_id INT,
    is_active BOOLEAN DEFAULT TRUE,

    FOREIGN KEY (venue_id) REFERENCES Venue(venue_id),
    FOREIGN KEY (category_id) REFERENCES EventCategory(category_id),
    FOREIGN KEY (created_by_user_id) REFERENCES User(user_id)
);
CREATE TABLE EventDay (
    event_day_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    day_date DATE NOT NULL,
    day_price DECIMAL(8,2),
    start_datetime DATETIME,
    end_datetime DATETIME,

    FOREIGN KEY (event_id) REFERENCES Event(event_id)
);
CREATE TABLE Booking (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_day_id INT NOT NULL,
    booking_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    num_tickets INT NOT NULL,
    status VARCHAR(20), -- 'confirmed', 'cancelled'
    cancellation_datetime DATETIME,

    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (event_day_id) REFERENCES EventDay(event_day_id)
);
CREATE TABLE WaitingListEntry (
    wait_id INT AUTO_INCREMENT PRIMARY KEY,
    event_day_id INT NOT NULL,
    user_id INT NOT NULL,
    request_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20), -- 'waiting', 'offered', 'expired'
    converted_booking_id INT,

    FOREIGN KEY (event_day_id) REFERENCES EventDay(event_day_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (converted_booking_id) REFERENCES Booking(booking_id)
);