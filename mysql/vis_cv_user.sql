-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Jul 17, 2021 at 01:42 PM
-- Server version: 5.7.34-0ubuntu0.18.04.1
-- PHP Version: 7.2.24-0ubuntu0.18.04.8

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `vis_cv_user`
--

-- --------------------------------------------------------

--
-- Table structure for table `vis_collections`
--

CREATE TABLE `vis_collections` (
  `id` int(11) NOT NULL,
  `creator_id` int(11) NOT NULL,
  `created` datetime NOT NULL,
  `name` text NOT NULL,
  `comment` text NOT NULL,
  `status` tinyint(4) NOT NULL,
  `total_images` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `vis_collection_access`
--

CREATE TABLE `vis_collection_access` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `collection_id` int(11) NOT NULL,
  `priv` tinyint(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `vis_images`
--

CREATE TABLE `vis_images` (
  `id` int(11) NOT NULL,
  `collection_id` int(11) NOT NULL,
  `filename` text NOT NULL,
  `upload_date` datetime NOT NULL,
  `upload_user` int(11) NOT NULL,
  `status` tinyint(4) NOT NULL,
  `orig_filename` text NOT NULL,
  `artist` text CHARACTER SET utf8,
  `title` text CHARACTER SET utf8,
  `date` text CHARACTER SET utf8,
  `genre` text CHARACTER SET utf8,
  `epoch` text CHARACTER SET utf8,
  `measurements` text CHARACTER SET utf8,
  `material` text CHARACTER SET utf8,
  `technique` text CHARACTER SET utf8,
  `institution` text CHARACTER SET utf8,
  `provenance` text CHARACTER SET utf8,
  `iconclass` text CHARACTER SET utf8,
  `year` smallint(6) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `vis_index_types`
--

CREATE TABLE `vis_index_types` (
  `id` int(11) NOT NULL,
  `name` tinytext NOT NULL,
  `description` text NOT NULL,
  `params` mediumtext NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `vis_indices`
--

CREATE TABLE `vis_indices` (
  `id` int(11) NOT NULL,
  `is_latest` tinyint(1) NOT NULL,
  `collection_id` int(11) NOT NULL,
  `creator_id` int(11) NOT NULL,
  `creation_date` datetime NOT NULL,
  `name` text NOT NULL,
  `status` smallint(6) NOT NULL,
  `total_images` int(11) NOT NULL,
  `type` int(11) NOT NULL,
  `params` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `exitcode` int(11) DEFAULT NULL,
  `worker_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `vis_jobs`
--

CREATE TABLE `vis_jobs` (
  `id` int(11) NOT NULL,
  `type` int(11) NOT NULL,
  `item_id` int(11) NOT NULL,
  `params` text CHARACTER SET utf8 NOT NULL,
  `creator_id` int(11) NOT NULL,
  `registration_time` datetime NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `exitcode` int(11) DEFAULT NULL,
  `status` int(11) NOT NULL,
  `worker_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `vis_searches`
--

CREATE TABLE `vis_searches` (
  `id` int(11) NOT NULL,
  `name` mediumtext NOT NULL,
  `index_id` int(11) NOT NULL,
  `collection_id` int(11) NOT NULL,
  `refined_search` text,
  `base_search` int(11) DEFAULT NULL,
  `creator_id` int(11) NOT NULL,
  `creation_date` datetime NOT NULL,
  `score` float NOT NULL,
  `total_hits` int(11) NOT NULL,
  `image_id` int(11) NOT NULL,
  `query_bbox` text NOT NULL,
  `params` text NOT NULL,
  `status` int(11) NOT NULL,
  `group_id` int(11) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `exitcode` int(11) DEFAULT NULL,
  `worker_id` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `vis_search_favorites`
--

CREATE TABLE `vis_search_favorites` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `search_id` int(11) NOT NULL,
  `element_list` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `vis_search_groups`
--

CREATE TABLE `vis_search_groups` (
  `id` int(11) NOT NULL,
  `name` text NOT NULL,
  `members` int(11) NOT NULL,
  `collection_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `vis_search_results`
--

CREATE TABLE `vis_search_results` (
  `id` int(11) NOT NULL,
  `image_id` int(11) NOT NULL,
  `search_id` int(11) NOT NULL,
  `score` float NOT NULL,
  `vote` tinyint(4) NOT NULL,
  `total_boxes` smallint(6) NOT NULL,
  `box_data` text NOT NULL,
  `box_scores` mediumtext NOT NULL,
  `refined_searchbox` text,
  `tsne` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `vis_users`
--

CREATE TABLE `vis_users` (
  `id` int(11) NOT NULL,
  `name` text NOT NULL,
  `password` text NOT NULL,
  `time_limit` datetime NOT NULL,
  `coll_priv` tinyint(4) NOT NULL,
  `user_priv` tinyint(4) NOT NULL,
  `resource_priv` tinyint(4) NOT NULL,
  `status` tinyint(4) NOT NULL,
  `session_id` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `vis_users`
--

INSERT INTO `vis_users` (`id`, `name`, `password`, `time_limit`, `coll_priv`, `user_priv`, `resource_priv`, `status`, `session_id`) VALUES
(1, 'test', '098f6bcd4621d373cade4e832627b4f6', '2021-09-24 12:48:40', 4, 2, 2, 0, 'frqqv664j8e7acqju104uquum6');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `vis_collections`
--
ALTER TABLE `vis_collections`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `vis_collection_access`
--
ALTER TABLE `vis_collection_access`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `vis_images`
--
ALTER TABLE `vis_images`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`),
  ADD KEY `collection_id` (`collection_id`);
ALTER TABLE `vis_images` ADD FULLTEXT KEY `orig_filename` (`orig_filename`);
ALTER TABLE `vis_images` ADD FULLTEXT KEY `kuenstler_2` (`artist`,`title`,`date`,`genre`,`epoch`,`measurements`,`material`,`technique`,`institution`,`provenance`,`iconclass`);

--
-- Indexes for table `vis_index_types`
--
ALTER TABLE `vis_index_types`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`);

--
-- Indexes for table `vis_indices`
--
ALTER TABLE `vis_indices`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`);

--
-- Indexes for table `vis_jobs`
--
ALTER TABLE `vis_jobs`
  ADD UNIQUE KEY `id` (`id`);

--
-- Indexes for table `vis_searches`
--
ALTER TABLE `vis_searches`
  ADD PRIMARY KEY (`id`);
ALTER TABLE `vis_searches` ADD FULLTEXT KEY `name` (`name`);

--
-- Indexes for table `vis_search_favorites`
--
ALTER TABLE `vis_search_favorites`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `vis_search_groups`
--
ALTER TABLE `vis_search_groups`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`);

--
-- Indexes for table `vis_search_results`
--
ALTER TABLE `vis_search_results`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `vis_users`
--
ALTER TABLE `vis_users`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `vis_collections`
--
ALTER TABLE `vis_collections`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_collection_access`
--
ALTER TABLE `vis_collection_access`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_images`
--
ALTER TABLE `vis_images`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_index_types`
--
ALTER TABLE `vis_index_types`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_indices`
--
ALTER TABLE `vis_indices`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_jobs`
--
ALTER TABLE `vis_jobs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_searches`
--
ALTER TABLE `vis_searches`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_search_favorites`
--
ALTER TABLE `vis_search_favorites`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_search_groups`
--
ALTER TABLE `vis_search_groups`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_search_results`
--
ALTER TABLE `vis_search_results`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vis_users`
--
ALTER TABLE `vis_users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
