import logging
import os
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings


service = BlobServiceClient.from_connection_string(
    conn_str=os.environ['AzureWebJobsStorage'])


def main(req: func.HttpRequest, queue: func.Out[func.QueueMessage], saveDetails: func.Out[func.Document], getBooks: func.DocumentList) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    book_title = req.form.get('book_title') or req.params.get('book_title')
    author = req.form.get('author') or req.params.get('author')
    if not book_title or not author:
        return func.HttpResponse(
            "Please pass a book title and author on the query string or in the request body",
            status_code=400
        )
    bookId = "".join("{:02x}".format(ord(c)) for c in author+book_title)

    existing_books = getBooks
    if len(existing_books) > 0:
        return func.HttpResponse(
            "Book already exists",
            status_code=400
        )

    try:
        blob_container = service.create_container(bookId, public_access="blob")
    except Exception:
        return func.HttpResponse(
            "Error creating container",
            status_code=400
        )
    cover = req.files.get('cover')
    if not cover:
        return func.HttpResponse(
            "Please pass a cover image on the query string or in the request body",
            status_code=400
        )
    content_settings = ContentSettings(content_type=cover.content_type)
    blob_container.upload_blob(
        name="cover." + cover.filename.rsplit('.', 1)[1].lower(), data=cover, content_settings=content_settings)
    for file in req.files.values():
        if not file.filename.startswith("ch"):
            continue
        content_settings = ContentSettings(content_type=file.content_type)
        blob_container.upload_blob(
            name=file.filename, data=file, content_settings=content_settings)
    queue.set(bookId)
    saveDetails.set(
        func.Document.from_dict(
            {
                "id": bookId,
                "bookName": book_title,
                "author": author,
                "cover": "https://manimbookupload.blob.core.windows.net/" + bookId + "/cover." + cover.filename.rsplit('.', 1)[1].lower(),
                "status": "uploaded"
            })
    )

    return func.HttpResponse(f"Book {book_title} by {author} uploaded with id {bookId}")
