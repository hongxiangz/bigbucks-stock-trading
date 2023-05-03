DROP DATABASE IF EXISTS stock;

create database stock default character set utf8 collate utf8_bin;

USE stock;

/* create user table */
DROP TABLE IF EXISTS `Users`;
CREATE TABLE `Users` (
    `pk` INT PRIMARY KEY AUTO_INCREMENT,
    `username` varchar(255) NOT NULL UNIQUE,
    `password` varchar(255) NOT NULL,
    `balance` FLOAT NOT NULL,
    `current_date` DATE,
    `role` varchar(255) NOT NULL
);

/* create stock table */
DROP TABLE IF EXISTS `Stocks`;
CREATE TABLE `Stocks` (
  `pk` INT PRIMARY KEY AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `price` FLOAT,
  `date` DATE
);

DROP TABLE IF EXISTS `Transactions`;
CREATE TABLE `Transactions` (
  `pk` INT PRIMARY KEY AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `stock` VARCHAR(50) NOT NULL,
  `date` DATE NOT NULL,
  `type` ENUM('Buy', 'Sell') NOT NULL,
  `shares` INT NOT NULL,
  `price` FLOAT NOT NULL,
  `cost` FLOAT NOT NULL,
  `balance` FLOAT NOT NULL,
  FOREIGN KEY (`username`) REFERENCES `Users`(`username`)
);

CREATE TABLE `Holdings` (
  `pk` INT PRIMARY KEY AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `stock` VARCHAR(10) NOT NULL,
  `shares` FLOAT NOT NULL,
  `cost` FLOAT NOT NULL,
  `date` DATE NOT NULL,
  `price` FLOAT NOT NULL
);
