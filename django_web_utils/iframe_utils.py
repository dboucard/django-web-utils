#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Iframe utility functions
To use this module, you should create the following templates:
    400.html, 401.html, 403.html, 404.html, 405.html, 500.html
All these templates should be in a dir called iframe.
'''
import urllib
import traceback
import logging
# Django
from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
from django.core.exceptions import PermissionDenied


# classic errors classes
# ----------------------------------------------------------------------------
class IframeHttp400(Exception):
    pass


class IframeHttp401(Exception):
    pass


IframeHttp403 = PermissionDenied


IframeHttp404 = Http404


# iframe_view function
# ----------------------------------------------------------------------------
def iframe_view(function=None, methods=None, login_url=None, login_required=False):
    '''
    Returns 400, 401, 403, 404, 405 and 500 errors with Iframe template.
    The "methods" argument can be used to allow only some methods on a particular view.
    To allow several methods, use this format: "GET, PUT".
    '''
    def decorator(fct):
        def _wrapped_view(request, *args, **kwargs):
            # Check request method
            if methods and request.method not in methods:
                response = render(request, 'iframe/405.html', status=405)
                response['Allow'] = methods
                return response
            # Process view
            try:
                # Check authentication
                if login_required and not request.user.is_authenticated():
                    raise IframeHttp401()
                return fct(request, *args, **kwargs)
            except IframeHttp400:
                return render(request, 'iframe/400.html', status=400)
            except IframeHttp401:
                next = urllib.quote(request.get_full_path())
                if login_url:
                    url = login_url
                    if next:
                        url += '?' if '?' not in url else '&'
                        url += 'next=' + next
                    return HttpResponseRedirect(url)
                return render(request, 'iframe/401.html', {'next': next}, status=401)
            except IframeHttp403:
                next = urllib.quote(request.get_full_path())
                if not request.user.is_authenticated() and login_url:
                    url = login_url
                    if next:
                        url += '?' if '?' not in url else '&'
                        url += 'next=' + next
                    return HttpResponseRedirect(url)
                return render(request, 'iframe/403.html', {'next': next}, status=403)
            except IframeHttp404:
                return render(request, 'iframe/404.html', status=404)
            except Exception:
                logger = logging.getLogger('django.request')
                logger.error('Internal server error: %s', request.get_full_path(), exc_info=traceback.extract_stack(), extra={'status_code': 500, 'request': request})
                return render(request, 'iframe/500.html', status=500)
        return _wrapped_view
    if function:
        return decorator(function)
    return decorator
