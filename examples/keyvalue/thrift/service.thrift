exception NotFoundError {
    1: string key,
}

service KeyValue {

    string getValue(
        1: string key,
    ) throws (
        1: NotFoundError notFound,
    )

    void setValue(
        1: string key,
        2: string value,
    )
}
