import os


def get_domain():
    return os.getenv("CLIENT_DOMAIN")


def get_password_reset_link(token):
    return "{}/{}?token={}".format(get_domain(), os.getenv("CLIENT_RESET_PASSWORD_ROUTE"), token)


def get_activate_account_link(token, uid):
    """

    :rtype: object
    """
    return "{}/{}?token={}&uid={}".format(get_domain(), os.getenv("CLIENT_ACTIVATE_ACCOUNT_ROUTE"), token, uid)


def get_article_link(slug):
    return "{}/{}/{}".format(get_domain(), os.getenv("CLIENT_READ_ARTICLE_ROUTE"), slug)
