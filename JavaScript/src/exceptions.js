export class TMsgpackEncodingError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TMsgpackEncodingError';
    }
}

export class TMsgpackDecodingError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TMsgpackDecodingError';
    }
}
