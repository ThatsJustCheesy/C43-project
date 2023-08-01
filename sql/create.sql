-- CSCC43 Project Schema

-- Listings(_id_, country, city, postal, address, lat, lon, type, amenities)

-- Users(_id_, sin, name, address, dob, occupation)
-- Hosts(_user_id_)
-- Renters(_user_id_, card_num)

-- BookingSlots(_id_, date)

-- Availability(_listing_id_, _slot_id_)
-- Bookings(_slot_id_, renter_id)

-- ListingComments(_renter_id_, _listing_id_, comment, rating)
-- UserComments(_renter_id_, _host_id_, renter_comment, renter_rating, host_comment, host_rating)

CREATE DATABASE IF NOT EXISTS mybnb;
USE mybnb;

CREATE TABLE Users (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,

  sin INTEGER UNIQUE NOT NULL,
  username VARCHAR(63) UNIQUE NOT NULL,
  name VARCHAR(127) NOT NULL,
  dob DATE NOT NULL,
  address VARCHAR(127),
  occupation VARCHAR(31)
);

CREATE TABLE Hosts (
  user_id INTEGER PRIMARY KEY,

  FOREIGN KEY (user_id) REFERENCES Users(id)
);

CREATE TABLE Renters (
  user_id INTEGER PRIMARY KEY,
  card_num CHAR(15),

  FOREIGN KEY (user_id) REFERENCES Users(id)
);


CREATE TABLE Listings (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  owner_id INTEGER NOT NULL,

  country VARCHAR(31) NOT NULL,
  city VARCHAR(31) NOT NULL,
  postal CHAR(6) NOT NULL,
  address VARCHAR(127) NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  type VARCHAR(31) NOT NULL,
  amenities VARCHAR(255) NOT NULL,

  FOREIGN KEY (owner_id) REFERENCES Hosts(user_id)
);

CREATE TABLE BookingSlots (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  listing_id INTEGER,
  date DATE NOT NULL,

  FOREIGN KEY (listing_id) REFERENCES Listings(id),
  UNIQUE (listing_id, date)
);

CREATE TABLE Availability (
  slot_id INTEGER PRIMARY KEY,
  rental_price REAL NOT NULL,

  FOREIGN KEY (slot_id) REFERENCES BookingSlots(id),
  UNIQUE (slot_id, rental_price)
);

CREATE TABLE Bookings (
  slot_id INTEGER PRIMARY KEY,
  renter_id INTEGER NOT NULL,
  cancelled BOOLEAN,

  FOREIGN KEY (slot_id) REFERENCES Availability(slot_id)
);

CREATE TABLE ListingComments (
  renter_id INTEGER,
  listing_id INTEGER,
  PRIMARY KEY (renter_id, listing_id),

  FOREIGN KEY (renter_id) REFERENCES Renters(user_id),
  FOREIGN KEY (listing_id) REFERENCES Listings(id),

  comment VARCHAR(511),
  rating INTEGER
);

CREATE TABLE UserComments (
  renter_id INTEGER,
  host_id INTEGER,
  PRIMARY KEY (renter_id, host_id),

  FOREIGN KEY (renter_id) REFERENCES Renters(user_id),
  FOREIGN KEY (host_id) REFERENCES Hosts(user_id),

  renter_comment VARCHAR(511),
  renter_rating INTEGER,
  host_comment VARCHAR(511),
  host_rating INTEGER
);
