typedef string UUID;

enum StatusCode {
    SUCCESS = 0
    FAILURE = 1
}

enum ArgScheme {
    RAW
    JSON
    THRIFT
}

struct TransportHeader {
    1: required binary key
    2: required binary value
}

struct Request {
    1: required string serviceName
    2: required string endpoint
    3: optional binary headers = ""
    4: required binary body

    /**
     * Remote hostport to which the request will be sent.
     *
     * If specified, the request will be made to this host only.
     */
    5: optional binary hostPort = ""
    6: optional ArgScheme argScheme = ArgScheme.RAW
    7: optional list<TransportHeader> transportHeaders = []

    /**
     * List of known peers of the TChannel at the time the request was made.
     *
     * This MUST be specified if hostPort wasn't. The request will be sent to
     * a random peer from the list.
     */
    8: optional list<binary> knownPeers = []
    // TODO: retry flags
    // TODO: timeout
    // TODO: tracing information
}

struct Response {
    1: required StatusCode code
    2: optional binary headers = ""
    3: required binary body
}

/**
 * Raised when the record mode for a cassette prevents recording new
 * interactions for it.
 */
exception CannotRecordInteractionsError {
    1: optional string message
}

/**
 * Raised when the remote service throws a protocol error.
 */
exception RemoteServiceError {
    1: required byte code
    2: required string message
}

/**
 * Raised when both, hostPort and knownPeers were empty so the system couldn't
 * make a request.
 */
exception NoPeersAvailableError {
    1: required string message
}

/**
 * A generic error for VCR exceptions not covered elsewhere.
 */
exception VCRServiceError {
    1: optional string message
}


/**
 * The VCRProxy service is responsible for forwarding requests to the remote
 * server, recording the interactions, and replaying responses for known
 * requests.
 */
service VCRProxy {
    /**
     * Send the given request through the system.
     *
     * If the request is known, replay its response. Otherwise, forward it to
     * the remote server and return the remote server's response.
     */
    Response send(
        1: Request request,
    ) throws (
        /**
         * Thrown if the request was unrecognized and the record mode for the
         * current cassette disallows recording new interactions.
         */
        1: CannotRecordInteractionsError cannotRecord,
        2: RemoteServiceError remoteServiceError,
        3: VCRServiceError serviceError,
        4: NoPeersAvailableError noPeersAvailable,
    );
}
