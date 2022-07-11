# **Task 1: Data Extraction, Batch Processing with Hadoop**

Questions
For each task, you must answer a subset of the following questions. Each question is over the entire dataset, unless otherwise specified.

Group 1 (Answer any 2):

Rank the top 10 most popular airports by numbers of flights to/from the airport.
Rank the top 10 airlines by on-time arrival performance.
Rank the days of the week by on-time arrival performance.
Group 2 (Answer any 3):

For Questions 1 and 2 below, we are asking you to find, for each airport, the top 10 carriers and destination airports from that airport with respect to on-time departure performance. We are not asking you to rank the overall top 10 carriers/airports. For specific queries, see the Task 1 Queries and Task 2 Queries.

For each airport X, rank the top-10 carriers in decreasing order of on-time departure performance from X.
For each airport X, rank the top-10 airports in decreasing order of on-time departure performance from X.
For each source-destination pair X-Y, rank the top-10 carriers in decreasing order of on-time arrival performance at Y from X.
For each source-destination pair X-Y, determine the mean arrival delay (in minutes) for a flight from X to Y.
Group 3 (Answer both questions using Hadoop. You may also use Spark Streaming to answer Question 2.):

Does the popularity distribution of airports follow a Zipf distribution? If not, what distribution does it follow?
Tom wants to travel from airport X to airport Z. However, Tom also wants to stop at airport Y for some sightseeing on the way. More concretely, Tom has the following requirements (for specific queries, see the Task 1 Queries and Task 2 Queries):
a) The second leg of the journey (flight Y-Z) must depart two days after the first leg (flight X-Y). For example, if X-Y departs on January 5, 2008, Y-Z must depart on January 7, 2008.

b) Tom wants his flights scheduled to depart airport X before 12:00 PM local time and to depart airport Y after 12:00 PM local time.

c) Tom wants to arrive at each destination with as little delay as possible. You can assume you know the actual delay of each flight.

Your mission (should you choose to accept it!) is to find, for each X-Y-Z and day/month (dd/mm) combination in the year 2008, the two flights (X-Y and Y-Z) that satisfy constraints (a) and (b) and have the best individual performance with respect to constraint (c), if such flights exist.

For the queries in Group 2 and Question 3.2, you will need to compute the results for ALL input values (e.g., airport X, source-destination pair X-Y, etc.) for which the result is nonempty. These results should then be stored in Cassandra so that the results for an input value can be queried by a user. Then, closer to the grading deadline, we will give you sample queries (airports, flights, etc.) to include in your video demo and report.

For example, after completing Question 2.2, a user should be able to provide an airport code (such as “ATL”) and receive the top 10 airports in decreasing order of on-time departure performance from ATL. Note that for questions such as 2.3, you do not need to compute the values for all possible combinations of X-Y, but rather only for those such that a flight from X to Y exists.


https://blog.insightdatascience.com/spinning-up-a-free-hadoop-cluster-step-by-step-c406d56bae42
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-attaching-volume.html
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-using-volumes.html

1. start EC2 / micro -  4nodes : 1 NameNode + 3 datanode
2. attacj volume https://aws.amazon.com/datasets/transportation-databases/
