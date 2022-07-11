# **Big Data Processing**

Store and process large airline transportation dataset to answer different types of queries. we will process in batch processing modes (using Hadoop/Cassandra, and separately using Spark) and stream processing mode (using Storm).


---
Project Specification
---

The project will use a [transportation dataset](https://aws.amazon.com/datasets/transportation-databases/) from the US Bureau of Transportation Statistics (BTS) that is hosted as an Amazon EBS volume snapshot.

The dataset used in the Project contains data and statistics from the US Department of Transportation on aviation, maritime, highway, transit, rail, pipeline, bike/pedestrian, and other modes of transportation in CSV format. The data is described in more detail by the [Bureau of Transportation Statistics](https://www.transtats.bts.gov/DataIndex.asp). (Note that the dataset we are using does not extend beyond 2008, although more recent data is available from the previous link.) In this Project, we will concentrate exclusively on the aviation portion of the dataset, which contains flight data such as departure and arrival delays, flight times, etc. For an example of analysis using this dataset, see Which flight will get you there fastest?

We will process database with both batch processing systems (Apache Hadoop and Spark), and in a stream processing system (Apache Storm). 

The set of questions that must be answered using this dataset is provided in the next section. These questions involve discovering useful information such as the best day of week to fly to minimize delays, the most popular airports, the most on-time airlines, etc. Each task will require you to answer a subset of these questions using a particular set of distributed systems. The exact methodology used to answer the questions is largely left to you, but you must integrate and utilize the specified systems to arrive at your answers.