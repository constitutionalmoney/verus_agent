const { VDXFObject } = require('verus-typescript-primitives/dist/vdxf');
const bufferutils = require('verus-typescript-primitives/dist/utils/bufferutils');
const { BufferReader, BufferWriter } = bufferutils.default;

/**
 * Custom ChessGame VDXF class for compact serialization
 * This class extends VDXFObject and implements efficient serialization
 * to minimize transaction fees and improve performance
 */
class ChessGame extends VDXFObject {
  constructor(gameId, white, black, winner = null, status = 'active', moves = [], timestamp = null) {
    super();
    this.gameId = gameId;
    this.white = white;
    this.black = black;
    this.winner = winner;
    this.status = status;
    this.moves = moves;
    this.timestamp = timestamp || new Date().toISOString();
    this.hash = this.calculateHash();
  }
  
  /**
   * Convert chess move to uint16 (e.g., "e2e4" -> 0x6562, 0x6534)
   */
  moveToUint16(move) {
    if (!move || move.length !== 4) return 0;
    
    const fromSquare = move.substring(0, 2);
    const toSquare = move.substring(2, 4);
    
    // Convert squares to uint16: file (0-7) + rank (0-7) * 8
    const fromFile = fromSquare.charCodeAt(0) - 'a'.charCodeAt(0);
    const fromRank = 8 - parseInt(fromSquare[1]);
    const toFile = toSquare.charCodeAt(0) - 'a'.charCodeAt(0);
    const toRank = 8 - parseInt(toSquare[1]);
    
    const fromCoord = fromFile + fromRank * 8;
    const toCoord = toFile + toRank * 8;
    
    return (fromCoord << 8) | toCoord;
  }
  
  /**
   * Convert uint16 back to chess move
   */
  uint16ToMove(moveUint16) {
    const fromCoord = (moveUint16 >> 8) & 0xFF;
    const toCoord = moveUint16 & 0xFF;
    
    const fromFile = fromCoord % 8;
    const fromRank = Math.floor(fromCoord / 8);
    const toFile = toCoord % 8;
    const toRank = Math.floor(toCoord / 8);
    
    const fromSquare = String.fromCharCode('a'.charCodeAt(0) + fromFile) + (8 - fromRank);
    const toSquare = String.fromCharCode('a'.charCodeAt(0) + toFile) + (8 - toRank);
    
    return fromSquare + toSquare;
  }
  
  /**
   * Calculate SHA256 hash of the game data
   */
  calculateHash() {
    const data = `${this.gameId}${this.white}${this.black}${this.winner || ''}${this.status}${this.moves.join('')}${this.timestamp}`;
    const crypto = require('crypto');
    return crypto.createHash('sha256').update(data).digest('hex');
  }
  
  /**
   * Calculate the byte length of the serialized data
   */
  getByteLength() {
    let length = 0;
    
    // Game ID (string with length prefix)
    length += 4; // uint32 for string length
    length += Buffer.byteLength(this.gameId, 'utf8');
    
    // White player (string with length prefix)
    length += 4; // uint32 for string length
    length += Buffer.byteLength(this.white, 'utf8');
    
    // Black player (string with length prefix)
    length += 4; // uint32 for string length
    length += Buffer.byteLength(this.black, 'utf8');
    
    // Winner (string with length prefix)
    length += 4; // uint32 for string length
    length += Buffer.byteLength(this.winner || '', 'utf8');
    
    // Moves array
    length += 4; // uint32 for array length
    for (const move of this.moves) {
      length += 4; // uint32 for string length
      length += Buffer.byteLength(move, 'utf8');
    }
    
    // Timestamp (uint64)
    length += 8;
    
    // Status (string with length prefix)
    length += 4; // uint32 for string length
    length += Buffer.byteLength(this.status, 'utf8');
    
    // Hash (string with length prefix)
    length += 4; // uint32 for string length
    length += Buffer.byteLength(this.hash, 'utf8');
    
    return length;
  }
  
  /**
   * Serialize the chess game data to a Buffer
   */
  toDataBuffer() {
    const bufferWriter = new BufferWriter(Buffer.alloc(this.getByteLength()));
    
    // Write Game ID
    const gameIdBuffer = Buffer.from(this.gameId, 'utf8');
    bufferWriter.writeUInt32(gameIdBuffer.length);
    bufferWriter.writeSlice(gameIdBuffer);
    
    // Write White player
    const whiteBuffer = Buffer.from(this.white, 'utf8');
    bufferWriter.writeUInt32(whiteBuffer.length);
    bufferWriter.writeSlice(whiteBuffer);
    
    // Write Black player
    const blackBuffer = Buffer.from(this.black, 'utf8');
    bufferWriter.writeUInt32(blackBuffer.length);
    bufferWriter.writeSlice(blackBuffer);
    
    // Write Winner
    const winnerBuffer = Buffer.from(this.winner || '', 'utf8');
    bufferWriter.writeUInt32(winnerBuffer.length);
    bufferWriter.writeSlice(winnerBuffer);
    
    // Write Moves array
    bufferWriter.writeUInt32(this.moves.length);
    for (const move of this.moves) {
      const moveBuffer = Buffer.from(move, 'utf8');
      bufferWriter.writeUInt32(moveBuffer.length);
      bufferWriter.writeSlice(moveBuffer);
    }
    
    // Write Timestamp
    bufferWriter.writeUInt64(this.timestamp);
    
    // Write Status
    const statusBuffer = Buffer.from(this.status, 'utf8');
    bufferWriter.writeUInt32(statusBuffer.length);
    bufferWriter.writeSlice(statusBuffer);
    
    // Write Hash
    const hashBuffer = Buffer.from(this.hash, 'utf8');
    bufferWriter.writeUInt32(hashBuffer.length);
    bufferWriter.writeSlice(hashBuffer);
    
    return bufferWriter.buffer;
  }
  
  /**
   * Deserialize chess game data from a Buffer
   */
  fromDataBuffer(buffer, offset = 0) {
    const reader = new BufferReader(buffer, offset);
    
    // Read Game ID
    const gameIdLength = reader.readUInt32();
    this.gameId = reader.readSlice(gameIdLength).toString('utf8');
    
    // Read White player
    const whiteLength = reader.readUInt32();
    this.white = reader.readSlice(whiteLength).toString('utf8');
    
    // Read Black player
    const blackLength = reader.readUInt32();
    this.black = reader.readSlice(blackLength).toString('utf8');
    
    // Read Winner
    const winnerLength = reader.readUInt32();
    this.winner = reader.readSlice(winnerLength).toString('utf8');
    
    // Read Moves array
    const movesLength = reader.readUInt32();
    this.moves = [];
    for (let i = 0; i < movesLength; i++) {
      const moveLength = reader.readUInt32();
      const move = reader.readSlice(moveLength).toString('utf8');
      this.moves.push(move);
    }
    
    // Read Timestamp
    this.timestamp = reader.readUInt64();
    
    // Read Status
    const statusLength = reader.readUInt32();
    this.status = reader.readSlice(statusLength).toString('utf8');
    
    // Read Hash
    const hashLength = reader.readUInt32();
    this.hash = reader.readSlice(hashLength).toString('utf8');
    
    return reader.offset;
  }
  
  /**
   * Convert to JSON representation
   */
  toJson() {
    return {
      gameId: this.gameId,
      white: this.white,
      black: this.black,
      winner: this.winner,
      moves: this.moves,
      timestamp: this.timestamp,
      status: this.status,
      hash: this.hash
    };
  }
  
  /**
   * Create ChessGame from JSON
   */
  static fromJson(data) {
    return new ChessGame(data.gameId, data.white, data.black, data.winner, data.status, data.moves, data.timestamp);
  }
  
  /**
   * Get compact string representation for debugging
   */
  toString() {
    return `ChessGame(${this.gameId}, ${this.white} vs ${this.black}, ${this.status})`;
  }
  
  /**
   * Get the size of serialized data in bytes
   */
  getSerializedSize() {
    return this.toDataBuffer().length;
  }
  
  /**
   * Get the size of JSON representation in bytes
   */
  getJsonSize() {
    return Buffer.byteLength(JSON.stringify(this.toJson()), 'utf8');
  }
  
  /**
   * Get compression ratio (JSON size / serialized size)
   */
  getCompressionRatio() {
    return this.getJsonSize() / this.getSerializedSize();
  }
  
  /**
   * Serialize to compact binary format
   */
  toCompactBuffer() {
    // Estimate buffer size: gameId + white + black + winner + status + moves + timestamp
    const estimatedSize = 1024; // Start with a reasonable size
    const buffer = Buffer.alloc(estimatedSize);
    const writer = new BufferWriter(buffer);
    
    // Write gameId as varSlice (variable length)
    writer.writeVarSlice(Buffer.from(this.gameId || '', 'utf-8'));
    
    // Write player names as varSlice
    writer.writeVarSlice(Buffer.from(this.white || '', 'utf-8'));
    writer.writeVarSlice(Buffer.from(this.black || '', 'utf-8'));
    
    // Write winner as varSlice (null if no winner)
    writer.writeVarSlice(Buffer.from(this.winner || '', 'utf-8'));
    
    // Write status as varSlice
    writer.writeVarSlice(Buffer.from(this.status || '', 'utf-8'));
    
    // Write moves as compact size + 4-byte slices
    writer.writeCompactSize(this.moves ? this.moves.length : 0);
    if (this.moves) {
        for (const move of this.moves) {
            // Convert move to 4-byte buffer (e.g., "e2e4" -> 4 bytes)
            const moveBuffer = Buffer.from(move || '    ', 'utf-8').slice(0, 4);
            writer.writeSlice(moveBuffer);
        }
    }
    
    // Write timestamp as varSlice
    writer.writeVarSlice(Buffer.from(this.timestamp || '', 'utf-8'));
    
    // Return only the used portion of the buffer
    return buffer.slice(0, writer.offset);
  }
  
  /**
   * Deserialize from compact binary format
   */
  static fromCompactBuffer(buffer) {
    const reader = new BufferReader(buffer);
    
    // Read gameId as varSlice
    const gameId = reader.readVarSlice().toString('utf-8');
    
    // Read player names as varSlice
    const white = reader.readVarSlice().toString('utf-8');
    const black = reader.readVarSlice().toString('utf-8');
    
    // Read winner as varSlice
    const winner = reader.readVarSlice().toString('utf-8') || null;
    
    // Read status as varSlice
    const status = reader.readVarSlice().toString('utf-8');
    
    // Read moves as compact size + 4-byte slices
    const moveCount = reader.readCompactSize();
    const moves = [];
    for (let i = 0; i < moveCount; i++) {
        const moveBuffer = reader.readSlice(4);
        const move = moveBuffer.toString('utf-8').trim();
        moves.push(move);
    }
    
    // Read timestamp as varSlice
    const timestamp = reader.readVarSlice().toString('utf-8');
    
    return new ChessGame(gameId, white, black, winner, status, moves, timestamp);
  }

  toJSON() {
    return {
      gameId: this.gameId,
      white: this.white,
      black: this.black,
      winner: this.winner,
      status: this.status,
      moves: this.moves,
      timestamp: this.timestamp,
      hash: this.hash
    };
  }
}

module.exports = { ChessGame }; 