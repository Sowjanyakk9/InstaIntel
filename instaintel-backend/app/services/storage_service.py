def upload_file(file):

    file_path = f"datasets/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return file_path