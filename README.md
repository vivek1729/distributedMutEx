# distributedMutEx
Distributed Mutual Exclusion using Lamport logical clock

## 1 Application Component
We will assume multiple clients. The life of a client is boring:
- Read the post.
- Like the post.

Clients are always curious about the number of likes associated with the post,
and do so by reading numOfLikes. Clients need to communicate with each other
to maintain the correct number of LIKEs.

## 2 Implementation Details
- Each client should store its own view of numOfLikes.
- Each client should maintain a Lamport logical clock. As discussed in the
lecture, we should use the Totally-Ordered Lamport Clock, ie,h(Lamportclock, P rocessidi
to break ties and each client should maintain its request queue.

## 3 User Interface
- When starting a client, it should connect to all the other clients. You can
provide a client’s IP, or other identification info that can uniquely identify
each client. Or this could be done via a configuration file or other methods
that are appropriate.
- A client should read the content of the post (not relevant for the purposes
of this assignment). It should display the content and the current number
of LIKEs (set to 0 when starting; kept up to date during the processing
of requests) on the screen.
- You should log all necessary information on the console for the sake of
debugging and demonstration, e.g. Message sent to client XX. Message
received from client YY. When the local clock value changes, output the
current clock value. When the LIKE count changes, output the current
LIKE count.
- You should add some delay (e.g. 5 seconds) when sending a message. This
simulates the time for message passing and makes it easier for demoing
concurrent events.
- Use message passing primitives TCP/UDP. You can decide which alternative
and explore the trade-offs. We will be interested in hearing your
experience.

## 4 Usage
- Start the server
`python application_for_post.py config.json`

- Start the client
`python client.py <client_id>`
