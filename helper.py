from flask import abort, Response, request


def throw_error(num, error):
    """
    Throws an HTTP error
    :param num: The HTTP error number
    :param error: An error message
    """
    abort(Response(error, num))


def print_functions(obj):
    """
    Prints all the objects of a given object.
    For debugging and development purposes.
    :param obj: The object
    """
    print(str(dir(obj)).replace(", ", "\n"))


def is_argument_present(name):
    """
    :param name: The argument name
    :return: Whether the argument was present in the URL
    """
    value = request.args.get(name)
    return value is not None and len(value) > 0


def is_argument_valid_type(name, type):
    """
    :param name: The argument name
    :param type: The argument type (STR, NUM)
    :return: Whether the argument is of the correct type
    """
    value = request.args.get(name)

    if type == "STR":
        try:
            str(value)
        except TypeError:
            return False

    if type == "NUM":
        try:
            value = int(value)
            if value < 0:
                return False
        except TypeError:
            return False

    return True


def validate_arguments(*args):
    """
    Validates the list of given arguments.
    Makes sure they are present and of the valid type.
    Arguments should be given in a list [arg, type].

    If any errors are found, they are displayed as an
    HTTP 400 error.
    :param args: A list of arguments and their types.
    """
    null = []
    invalid = []
    for arg in args:
        name = arg[0]
        type = arg[1]
        if not is_argument_present(name):
            null.append(name)
            continue

        if not is_argument_valid_type(name, type):
            invalid.append(name)

    returnString = ""
    if len(null) > 0:
        returnString += "<b>Missing arguments:</b> " + ', '.join(null) + ". "

    if len(invalid) > 0:
        returnString += "<b>Invalid arguments:</b> " + ', '.join(invalid) + ". "

    if len(returnString) > 0:
        throw_error(400, returnString)