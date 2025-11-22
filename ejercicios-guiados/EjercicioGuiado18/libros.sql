/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.5.27-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: Libros
-- ------------------------------------------------------
-- Server version	10.5.27-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Authors`
--

DROP TABLE IF EXISTS `Authors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Authors` (
  `author_id` int(11) NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  PRIMARY KEY (`author_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Authors`
--

LOCK TABLES `Authors` WRITE;
/*!40000 ALTER TABLE `Authors` DISABLE KEYS */;
INSERT INTO `Authors` VALUES (1,'Miguel','Cervantes'),(2,'Gabriel','García Márquez'),(3,'Isabel','Allende'),(4,'Julio','Cortázar'),(5,'Mario','Vargas Llosa'),(6,'Jorge Luis','Borges'),(7,'Laura','Esquivel'),(8,'Carlos','Fuentes'),(9,'Octavio','Paz'),(10,'Rosario','Castellanos');
/*!40000 ALTER TABLE `Authors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Books`
--

DROP TABLE IF EXISTS `Books`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Books` (
  `book_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `publisher` varchar(150) DEFAULT NULL,
  `year` int(11) DEFAULT NULL,
  `author_id` int(11) DEFAULT NULL,
  `genre_id` int(11) DEFAULT NULL,
  `format_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`book_id`),
  KEY `author_id` (`author_id`),
  KEY `genre_id` (`genre_id`),
  KEY `format_id` (`format_id`),
  CONSTRAINT `Books_ibfk_1` FOREIGN KEY (`author_id`) REFERENCES `Authors` (`author_id`),
  CONSTRAINT `Books_ibfk_2` FOREIGN KEY (`genre_id`) REFERENCES `Genres` (`genre_id`),
  CONSTRAINT `Books_ibfk_3` FOREIGN KEY (`format_id`) REFERENCES `Formats` (`format_id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Books`
--

LOCK TABLES `Books` WRITE;
/*!40000 ALTER TABLE `Books` DISABLE KEYS */;
INSERT INTO `Books` VALUES (1,'Don Quijote de la Mancha','Alfaguara',1605,1,2,1),(2,'Cien Años de Soledad','Sudamericana',1967,2,3,2),(3,'La Casa de los Espíritus','Plaza & Janés',1982,3,3,1),(4,'Rayuela','Sudamericana',1963,4,9,1),(5,'La Ciudad y los Perros','Seix Barral',1963,5,9,2),(6,'El Aleph','Emecé',1949,6,10,1),(7,'Como Agua para Chocolate','Planeta',1989,7,8,2),(8,'La Muerte de Artemio Cruz','Fondo de Cultura Económica',1962,8,9,1),(9,'El Laberinto de la Soledad','Fondo de Cultura Económica',1950,9,5,3),(10,'Balún Canán','Fondo de Cultura Económica',1957,10,9,2),(11,'El Amor en los Tiempos del Cólera','Oveja Negra',1985,2,8,1),(12,'Paula','Plaza & Janés',1994,3,9,3),(13,'Los Cachorros','Seix Barral',1967,5,9,2),(14,'Ficciones','Emecé',1944,6,2,1),(15,'Loba Negra','Planeta',2019,7,7,2),(16,'Aura','Era',1962,8,9,3),(17,'Piedra de Sol','Fondo de Cultura Económica',1957,9,4,1),(18,'Oficio de Tinieblas','Fondo de Cultura Económica',1962,10,9,2),(19,'Crónica de una Muerte Anunciada','La Oveja Negra',1981,2,3,1),(20,'Conversación en La Catedral','Seix Barral',1969,5,9,2);
/*!40000 ALTER TABLE `Books` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Formats`
--

DROP TABLE IF EXISTS `Formats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Formats` (
  `format_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`format_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Formats`
--

LOCK TABLES `Formats` WRITE;
/*!40000 ALTER TABLE `Formats` DISABLE KEYS */;
INSERT INTO `Formats` VALUES (1,'Hardcover'),(2,'Paperback'),(3,'eBook'),(4,'Audiobook');
/*!40000 ALTER TABLE `Formats` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Genres`
--

DROP TABLE IF EXISTS `Genres`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Genres` (
  `genre_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`genre_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Genres`
--

LOCK TABLES `Genres` WRITE;
/*!40000 ALTER TABLE `Genres` DISABLE KEYS */;
INSERT INTO `Genres` VALUES (1,'Novel'),(2,'Classic'),(3,'Magic Realism'),(4,'Poetry'),(5,'Essay'),(6,'History'),(7,'Fantasy'),(8,'Romance'),(9,'Drama'),(10,'Short Story');
/*!40000 ALTER TABLE `Genres` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-10-03  0:23:41
