//! `shimpz-store healthcheck`: one bounded `GET /api/health` to the local Store, so the image needs no shell.

use std::{
    io::{Read, Write},
    net::{Ipv4Addr, SocketAddr, TcpStream},
    time::Duration,
};

const TIMEOUT: Duration = Duration::from_secs(2);
const RESPONSE_LIMIT: u64 = 4096;
const REQUEST: &[u8] = b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";

/// Whether the Store on loopback `port` answers its health route with 200 and `{"status":"ok"}` within 2 s for each
/// socket operation.
#[must_use]
pub fn healthy(port: u16) -> bool {
    let address = SocketAddr::from((Ipv4Addr::LOCALHOST, port));
    let Ok(mut stream) = TcpStream::connect_timeout(&address, TIMEOUT) else {
        return false;
    };
    let mut response = Vec::new();
    // Any failed step leaves the response short of a healthy one, so only the bytes read decide.
    let _exchanged = stream
        .set_read_timeout(Some(TIMEOUT))
        .and(stream.set_write_timeout(Some(TIMEOUT)))
        .and_then(|()| stream.write_all(REQUEST))
        .and_then(|()| (&stream).take(RESPONSE_LIMIT).read_to_end(&mut response));
    healthy_response(&response)
}

/// A 200 whose body is exactly `{"status":"ok"}`.
fn healthy_response(response: &[u8]) -> bool {
    response.starts_with(b"HTTP/1.1 200 OK\r\n")
        && response.ends_with(b"\r\n\r\n{\"status\":\"ok\"}")
}

#[cfg(test)]
mod tests {
    use std::{io::Write, net::TcpListener, thread};

    use super::{healthy, healthy_response};

    #[test]
    fn only_the_exact_healthy_response_passes() {
        assert!(healthy_response(
            b"HTTP/1.1 200 OK\r\ncontent-length: 15\r\n\r\n{\"status\":\"ok\"}"
        ));
        assert!(!healthy_response(
            b"HTTP/1.1 503 Service Unavailable\r\n\r\n{\"status\":\"ok\"}"
        ));
        assert!(!healthy_response(
            b"HTTP/1.1 200 OK\r\n\r\n{\"status\":\"down\"}"
        ));
    }

    #[test]
    fn a_listener_answering_the_health_route_is_healthy_and_a_closed_port_is_not() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut request = [0; 256];
            let _ = std::io::Read::read(&mut stream, &mut request);
            stream
                .write_all(b"HTTP/1.1 200 OK\r\ncontent-length: 15\r\n\r\n{\"status\":\"ok\"}")
                .unwrap();
        });
        assert!(healthy(port));
        server.join().unwrap();
        assert!(!healthy(port));
    }
}
