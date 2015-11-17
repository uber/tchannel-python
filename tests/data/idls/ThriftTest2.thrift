union Value {
    1: string stringValue
    2: i32 integerValue
}

struct Item {
    1: required string key
    2: required Value value
}

exception ItemAlreadyExists {
    1: required Item item
    2: optional string message
}

exception ItemDoesNotExist {
    1: required string key
}

service Service {
    // oneway void putItemAsync(1: Item item);
    // TODO: oneway not yet supported

    void putItem(1: Item item, 2: bool failIfPresent)
         throws (1: ItemAlreadyExists alreadyExists);
    Item getItem(1: string key)
         throws (1: ItemDoesNotExist doesNotExist);

    bool healthy();
}
