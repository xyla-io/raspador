CREATE DATABASE testraspador;

CREATE USER 'testraspador' IDENTIFIED BY 'TESTPASSWORDZqHZqzI1EpJZ!';

GRANT ALL PRIVILEGES ON `testraspador`.* TO 'testraspador';

CREATE TABLE `testraspador`.`scrape_test` (
  `id` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `type` varchar(255) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `metadata` varchar(2046) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `configuration` varchar(255) NOT NULL,
  `fetch_date` datetime NOT NULL,
  
  UNIQUE KEY `point` (`id`, `title`, `date`)
);