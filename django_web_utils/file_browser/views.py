#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import datetime
from PIL import Image
# Django
from django.shortcuts import render
from django.template import defaultfilters
from django.http import Http404, HttpResponse
from django.utils.translation import ugettext_lazy as _
# Django web utils
from django_web_utils import json_utils
from django_web_utils.files_utils import get_unit, get_size
from django_web_utils.file_browser import config


IMAGES_EXTENSION = ['png', 'gif', 'bmp', 'tiff', 'jpg', 'jpeg']


# storage_manager
# ----------------------------------------------------------------------------
@config.view_decorator
def storage_manager(request):
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'file_browser/base.html'
    return render(request, tplt, {
        'base_url': config.BASE_URL,
    })


# storage_dirs
# ----------------------------------------------------------------------------
def recursive_dirs(path):
    dirs = list()
    files_names = os.listdir(path)
    files_names.sort(lambda a, b: cmp(a.lower(), b.lower()))
    for file_name in files_names:
        if '\'' in file_name or '"' in file_name:
            continue
        current_path = os.path.join(path, file_name)
        if os.path.isdir(current_path):
            dirs.append(dict(dir_name=file_name, sub_dirs=recursive_dirs(current_path)))
    return dirs


@config.view_decorator
def storage_dirs(request):
    base_path = config.BASE_PATH

    if not os.path.exists(base_path):
        return json_utils.failure_response(message=unicode(_('Folder "%s" does not exist') % base_path))

    return json_utils.success_response(dirs=recursive_dirs(base_path))


# storage_content
# ----------------------------------------------------------------------------
def sort_by_name(a, b, asc=True):
    if a['isdir'] and not b['isdir']:
        return -1
    elif not a['isdir'] and b['isdir']:
        return 1
    elif asc:
        return cmp(a['name'].lower(), b['name'].lower())
    else:
        return -cmp(a['name'].lower(), b['name'].lower())


def sort_by_size(a, b, asc=True):
    if a['isdir'] and not b['isdir']:
        return -1
    elif not a['isdir'] and b['isdir']:
        return 1
    elif asc:
        diff = cmp(a['size'], b['size'])
    else:
        diff = -cmp(a['size'], b['size'])
    if diff == 0:
        return cmp(a['name'].lower(), b['name'].lower())
    else:
        return diff


def sort_by_mdate(a, b, asc=True):
    if a['isdir'] and not b['isdir']:
        return -1
    elif not a['isdir'] and b['isdir']:
        return 1
    elif a['isdir'] and b['isdir']:
        diff = 0
    elif asc:
        diff = cmp(a['mdate'], b['mdate'])
    else:
        diff = -cmp(a['mdate'], b['mdate'])
    if diff == 0:
        return cmp(a['name'].lower(), b['name'].lower())
    else:
        return diff


@config.view_decorator
def storage_content(request):
    base_path = config.BASE_PATH
    path = request.GET.get('path')
    folder_path = base_path if not path else os.path.join(base_path, path)

    if not os.path.exists(folder_path):
        return json_utils.failure_response(message=unicode(_('Folder "%s" does not exist') % path))

    files_names = os.listdir(folder_path)
    if '.htaccess' in files_names:
        files_names.remove('.htaccess')

    # content list
    total_size = 0
    files = list()
    folder_index = 0
    for file_name in files_names:
        current_path = os.path.join(folder_path, file_name)
        size = get_size(current_path)
        total_size += size
        file_properties = {
            'name': file_name,
            'size': size,
            'sizeh': u'%s %s' % get_unit(size),
            'isdir': False,
        }
        if os.path.isdir(current_path):
            file_properties['isdir'] = True
            files.insert(folder_index, file_properties)
            folder_index += 1
        elif os.path.isfile(current_path):
            splitted = file_name.split('.')
            file_properties['ext'] = splitted[-1].lower() if len(splitted) > 0 else ''
            if file_properties['ext'] in IMAGES_EXTENSION and size < 10485760:
                # allow previes for images < 10MB
                file_properties['preview'] = True
            # get modification time
            mdate = datetime.datetime.fromtimestamp(os.path.getmtime(current_path)).strftime('%Y-%m-%d %H:%M')
            file_properties['mdate'] = mdate
            files.append(file_properties)
        # else: socket or other, ignored
    total_size = u'%s %s' % get_unit(total_size)
    folders_count = folder_index
    files_count = len(files) - folder_index

    # ordering
    order = request.GET.get('order', 'name-asc')
    if order == 'name-asc':
        files.sort(lambda a, b: sort_by_name(a, b))
    elif order == 'name-desc':
        files.sort(lambda a, b: sort_by_name(a, b, asc=False))
    elif order == 'size-asc':
        files.sort(lambda a, b: sort_by_size(a, b))
    elif order == 'size-desc':
        files.sort(lambda a, b: sort_by_size(a, b, asc=False))
    elif order == 'mdate-asc':
        files.sort(lambda a, b: sort_by_mdate(a, b))
    elif order == 'mdate-desc':
        files.sort(lambda a, b: sort_by_mdate(a, b, asc=False))
    else:
        files.sort(lambda a, b: sort_by_name(a, b))

    if path:
        files.insert(0, {
            'name': 'parent',
            'formated_name': u'← %s' % _('Parent folder'),
            'isdir': True,
            'isprevious': True,
        })

    return json_utils.success_response(
        files=files,
        path=path,
        total_size=total_size,
        folders_count=folders_count,
        files_count=files_count,
    )


# storage_img_preview
# ----------------------------------------------------------------------------
@config.view_decorator
def storage_img_preview(request):
    base_path = config.BASE_PATH
    path = request.GET.get('path')
    if path.startswith('/'):
        path = path[1:]
    if not path:
        raise Http404()
    file_path = os.path.join(base_path, path)
    if not os.path.exists(file_path):
        raise Http404()

    image = Image.open(file_path)
    image.load()
    image.thumbnail((200, 64), Image.ANTIALIAS)

    if file_path.lower().endswith('jpg') or file_path.lower().endswith('jpeg'):
        response = HttpResponse(content_type='image/jpeg')
        image.save(response, 'JPEG', quality=85)
    else:
        response = HttpResponse(content_type='image/png')
        image.save(response, 'PNG')
    return response
