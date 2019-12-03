import json

from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.serializer_helpers import ReturnList


class BaseJSONRenderer(JSONRenderer):  # NOQA : E731
    """
    Use this class to render your response in the JSend API format.
    In your Views, add the following:
    renderer_names=('<singular>','<plural>')
    This will render your data based on the renderer_names.

    For example to render users,
    In the User view:

    renderer_names=('user','users')

    will render as follows:

    {
        'status': 'success',
        'data' : {
            'users':[

            ]
        }
    }

    and for the a single user
    {
        'status' : 'success',
        'data' :{
            'user' :{
            }
        }
    }
    """
    charset = 'utf-8'
    single = None
    many = None
    SUCCESS_STATUSES = [
        status.HTTP_200_OK,
        status.HTTP_201_CREATED,
        status.HTTP_202_ACCEPTED,
        status.HTTP_100_CONTINUE,
        status.HTTP_302_FOUND,
    ]

    def render(self, data, accepted_media_type=None, renderer_context=None):  # NOQA : E731
        view = renderer_context['view']

        stat = 'success' if renderer_context['response'].status_code in self.SUCCESS_STATUSES else 'error'
        if hasattr(view, 'renderer_names'):
            names = view.renderer_names
            if len(names) != 2:
                raise ValueError("renderer_names should have two items in the form: (<singular>, <plural>)")
            else:
                self.single, self.many = names[0], names[1]

        if hasattr(data, 'get'):
            errors = data.get('errors', data.get('detail', None))
            if errors is None:
                errors = data.get('message', None)

            # if there exist errors, set the status as error
            if errors is not None:
                message = errors
                # if there is only one error, use 'message' field to display the response
                if isinstance(message, str):
                    return json.dumps({
                        'status': stat,
                        'message': message
                    })
                else:
                    # for dictionary or list, use data to display the response
                    return json.dumps({
                        'status': stat,
                        'data': message
                    })

        if isinstance(data, ReturnList):
            return json.dumps({
                'status': stat,
                'data': {self.many: data} if self.many else data
            })

        return json.dumps({
            'status': stat,
            'data': {self.single: data} if self.single else data
        })


class RatingJSONRenderer(JSONRenderer):
    charset = 'utf-8'

    def render(self, data, media_type=None, renderer_context=None):
        # If the view throws an error (such as the user can't be authenticated
        # or something similar), `data` will contain an `errors` key. We want
        # the default JSONRenderer to handle rendering errors, so we need to
        # check for this case.
        errors = data.get('errors', None)

        if errors is not None:
            # As mentioned about, we will let the default JSONRenderer handle
            # rendering errors.
            return super().render(data)

        # Finally, we can render our data under the "user" namespace.
        return json.dumps({
            'rating': data
        })
