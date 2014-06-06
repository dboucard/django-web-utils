#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Emails utility functions

Optional settings:
    - EMAIL_CONTEXT_PROCESSOR:
        This var should point to a function. The object returned by the
        function must be a dict and should contain a valid sender field
        (something like '"name" <sender@address.com>').
    - EMAIL_ERROR_TEMPLATE:
        The template to use to prepare error report emails.
'''
import datetime
import traceback
import logging
logger = logging.getLogger('djwutils.emails_utils')
# Django
from django.template.loader import render_to_string
from django.template import Context
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils import translation
from django.core import mail
from django.conf import settings
# utils
import html_utils


# get context
#--------------------------------------------------------------------------------
def _get_context(request=None):
    if '_context_processor' not in globals():
        # Get context fct
        ctx_processor = None
        if getattr(settings, 'EMAIL_CONTEXT_PROCESSOR', None):
            ctx_processor = settings.EMAIL_CONTEXT_PROCESSOR
            try:
                module_name = ctx_processor.split('.')[-1]
                module_path = ctx_processor[:-len(module_name)-1]
                if not module_path:
                    module_path = '.'
                ctx_processor = __import__(module_path, fromlist=[module_name])
                ctx_processor = getattr(ctx_processor, module_name)
            except Exception, e:
                logger.error('Failed to import emails context processor: %s', e)
            else:
                if not hasattr(ctx_processor, '__call__'):
                    ctx_processor = lambda request: ctx_processor
        _context_processor = ctx_processor
    else:
        ctx_processor = _context_processor
    if not ctx_processor:
        ctx = None
    else:
        ctx = ctx_processor(request)
        if ctx and not isinstance(ctx, dict):
            logger.error('Emails context processor returned an invalid object for context (must be a dict): %s', ctx)
            ctx = None
    return ctx

# send_template_emails (to send emails with a template)
#--------------------------------------------------------------------------------
def send_template_emails(template, contexts=None, request=None, content_subtype='html'):
    # Get common context
    common_ctx = _get_context(request)
    # Prepare emails messages
    if not contexts:
        contexts = [dict()]
    elif not isinstance(contexts, (tuple, list)):
        contexts = [contexts]
    connection = None
    cur_lang = translation.get_language()
    for context in contexts:
        if common_ctx:
            ctx = dict(common_ctx)
            ctx.update(context)
        else:
            ctx = context
        # Get sender
        sender = ctx['sender'] if ctx.get('sender') else '"Default sender name" <sender@address.com>'
        # Search for receivers
        receivers = None
        if ctx.get('receiver'):
            if hasattr(ctx['receiver'], 'email'):
                # the receiver is a user model, use his information
                if hasattr(ctx['receiver'], 'emails_lang'):
                    ctx['lang'] = ctx['receiver'].emails_lang
                if ctx['receiver'].get_full_name():
                    receivers = ['"%s" <%s>' %(ctx['receiver'].get_full_name(), ctx['receiver'].email)]
                else:
                    receivers = [ctx['receiver'].email]
            else:
                receivers = [ctx['receiver']]
        if not receivers:
            receivers = ctx.get('receivers')
        if not receivers:
            # Send emails to managers if no email is given
            receivers = [a[1] for a in settings.MANAGERS]
        if not isinstance(receivers, (tuple, list)):
            logger.error('An email cannot be sent because the mail its receivers are invalid.\nReceivers: %s\nEmail context: %s', receivers, ctx)
            continue
        if not ctx.get('lang'):
            ctx['lang'] = 'en'
        translation.activate(ctx['lang'])
        content = render_to_string(template, ctx, Context(dict(LANGUAGE_CODE=ctx['lang'])))
        subject_start = content.index('<subject>')
        subject_end = content.index('</subject>')
        subject = content[subject_start+9:subject_end].strip()
        content = content[:subject_start]+content[subject_end+10:]
        for receiver in receivers:
            msg = mail.EmailMessage(subject.encode('utf-8'), content.encode('utf-8'), sender, [receiver])
            msg.content_subtype = content_subtype # by default, set email content type to html
            try:
                if not connection:
                    connection = mail.get_connection()
                connection.send_messages([msg])
            except Exception, e:
                msg = 'Error when trying to send emails.'
                logger.error('%s Receiver: %s.\n%s' %(msg, receiver, traceback.format_exc()))
                translation.activate(cur_lang)
                return False, '%s Error: %s' %(msg, e)
            else:
                logger.info(u'Mail with subject "%s" sent to "%s" (tplt).', subject, receiver)
    translation.activate(cur_lang)
    return True, ''

# send_emails (to send emails without template)
#--------------------------------------------------------------------------------
def send_emails(subject, content, receivers=None, request=None, content_subtype='html'):
    # Get common context
    ctx = _get_context(request)
    # Get sender
    sender = ctx['sender'] if ctx.get('sender') else '"Default sender name" <sender@address.com>'
    # Get receivers
    if not receivers:
        # Send emails to managers if no email is given
        receivers = [a[1] for a in settings.MANAGERS]
    elif not isinstance(receivers, list):
        receivers = [receivers]
    # Prepare emails messages
    connection = None
    for receiver in receivers:
        msg = mail.EmailMessage(subject.encode('utf-8'), content.encode('utf-8'), sender, [receiver])
        msg.content_subtype = content_subtype # by default, set email content type to html
        try:
            if not connection:
                connection = mail.get_connection()
            connection.send_messages([msg])
        except Exception, e:
            msg = 'Error when trying to send emails.'
            logger.error('%s Receiver: %s\n%s' %(msg, receiver, traceback.format_exc()))
            return False, '%s Error: %s' %(msg, e)
        else:
            logger.info(u'Mail with subject "%s" sent to "%s".', subject, receiver)
    return True, ''

# send_error_report_emails (to send last traceback)
#--------------------------------------------------------------------------------
def send_error_report_emails(title=None, error=None, receivers=None, request=None):
    if request:
        title = u' (%s)' %title if title else ''
        title = u'Error at %s%s' %(request.get_full_path(), title)
    elif title:
        title = u'Error report - %s' %title
    else:
        title = u'Error report'
    
    fieldset_style = u'style="margin-bottom: 8px; border: 1px solid #888; border-radius: 4px;"'
    content = u'<div style="margin-bottom: 8px;">Message sent at: %s</div>' %datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Error information
    if error:
        content += u'<fieldset %s>\n' %fieldset_style
        content += u'<legend><b> Error </b></legend>\n'
        content += u'<div>%s</div>\n' %escape(error).replace('\n', '<br/>')
        content += u'</fieldset>\n\n'
    # Traceback information
    content += u'<fieldset %s>\n' %fieldset_style
    content += u'<legend><b> Traceback </b></legend>\n'
    content += u'<div style="color: #800;">%s</div>\n' %html_utils.get_html_traceback()
    content += u'</fieldset>\n\n'
    # Request's info
    if request:
        left_col_style = u'vertical-align: top; color: #666; padding-right: 8px; text-align: right;'
        right_col_style = u'vertical-align: top;'
        # Main request's info
        content += u'<fieldset %s>\n' %fieldset_style
        content += u'<legend><b> Main request\'s info </b></legend>\n'
        content += u'<table>\n'
        content += u'<tr> <td style="%s"><b>HTTP_USER_AGENT</b></td>\n' %left_col_style
        content += u'     <td style="%s"><b>%s</b></td> </tr>\n' %(right_col_style, escape(request.META.get('HTTP_USER_AGENT', 'unknown')))
        content += u'<tr> <td style="%s"><b>REMOTE_ADDR</b></td>\n' %left_col_style
        content += u'     <td style="%s"><b>%s</b></td> </tr>\n' %(right_col_style, escape(request.META.get('REMOTE_ADDR', 'unknown')))
        content += u'</table>\n'
        content += u'</fieldset>\n\n'
        # Other request's info
        content += u'<fieldset %s>\n' %fieldset_style
        content += u'<legend><b> Other request\'s info </b></legend>\n'
        content += u'<table>\n'
        keys = request.META.keys()
        keys.sort()
        for key in keys:
            if key not in ('HTTP_USER_AGENT', 'REMOTE_ADDR'):
                content += u'<tr> <td style="%s">%s</td>\n' %(left_col_style, escape(key))
                content += u'     <td style="%s">%s</td> </tr>\n' %(right_col_style, escape(request.META[key]))
        content += u'</table>\n'
        content += u'</fieldset>\n'
    content = mark_safe(content)
    # Send emails
    tplt = getattr(settings, 'EMAIL_ERROR_TEMPLATE', None)
    if tplt:
        return send_template_emails(tplt, dict(
            request = request,
            title = title,
            error = error,
            content = content,
            receivers = receivers,
        ))
    else:
        return send_emails(title, content, receivers, request)
