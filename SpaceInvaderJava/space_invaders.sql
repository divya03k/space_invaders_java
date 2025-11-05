CREATE DATABASE space_invaders_db;

USE space_invaders_db;

CREATE TABLE leaderboard (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_name VARCHAR(50) NOT NULL UNIQUE,
    score INT DEFAULT 0,
    level INT DEFAULT 1,
    last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
select* from leaderboard;
