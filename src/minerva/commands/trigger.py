from contextlib import closing
import argparse
import sys

import yaml
import dateutil.parser
import dateutil.tz

from minerva.db import connect
from minerva.trigger.trigger import Trigger
from minerva.instance import MinervaInstance, load_yaml
from minerva.commands import show_rows


def setup_command_parser(subparsers):
    cmd = subparsers.add_parser(
        'trigger', help='command for administering triggers'
    )

    cmd_subparsers = cmd.add_subparsers()

    setup_create_parser(cmd_subparsers)
    setup_enable_parser(cmd_subparsers)
    setup_disable_parser(cmd_subparsers)
    setup_delete_parser(cmd_subparsers)
    setup_list_parser(cmd_subparsers)
    setup_update_weight_parser(cmd_subparsers)
    setup_create_notifications_parser(cmd_subparsers)


def setup_create_parser(subparsers):
    cmd = subparsers.add_parser(
        'create', help='command for creating triggers'
    )

    cmd.add_argument(
        'definition', type=argparse.FileType('r'),
        help='file containing trend store definition'
    )

    cmd.set_defaults(cmd=create_trigger_cmd)


def create_trigger_cmd(args):
    # trigger_config = yaml.load(args.definition, Loader=yaml.SafeLoader)
    instance = MinervaInstance.load()
    trigger = instance.load_trigger_from_file(args.definition)

    sys.stdout.write(
        "Creating trigger '{}' ...\n".format(trigger.name)
    )

    try:
        create_trigger(trigger)
    except Exception as exc:
        sys.stdout.write("Error:\n{}".format(str(exc)))
        raise exc

    sys.stdout.write("Done\n")


def create_trigger(trigger: Trigger):

    with closing(connect()) as conn:

        conn.autocommit = True

        trigger.create(conn)


def setup_enable_parser(subparsers):
    cmd = subparsers.add_parser(
        'enable', help='command for enabling triggers'
    )

    cmd.add_argument('name', help='name of trigger')

    cmd.set_defaults(cmd=enable_trigger_cmd)


def enable_trigger_cmd(args):
    with closing(connect()) as conn:
        conn.autocommit = True

        Trigger(args.name).set_enabled(conn, True)


def setup_disable_parser(subparsers):
    cmd = subparsers.add_parser(
        'disable', help='command for disabling triggers'
    )

    cmd.add_argument('name', help='name of trigger')

    cmd.set_defaults(cmd=disable_trigger_cmd)


def disable_trigger_cmd(args):
    with closing(connect()) as conn:
        conn.autocommit = True

        Trigger(args.name).set_enabled(conn, False)


def setup_delete_parser(subparsers):
    cmd = subparsers.add_parser(
        'delete', help='command for deleting triggers'
    )

    cmd.add_argument('name', help='name of trigger')

    cmd.set_defaults(cmd=delete_trigger_cmd)


def delete_trigger_cmd(args):
    with closing(connect()) as conn:
        conn.autocommit = True

        Trigger.delete_by_name(conn, args.name)


def setup_list_parser(subparsers):
    cmd = subparsers.add_parser(
        'list', help='command for listing triggers'
    )

    cmd.set_defaults(cmd=list_cmd)


def setup_update_weight_parser(subparsers):
    cmd = subparsers.add_parser(
        'update-weight', help='command for updating the weight of a trigger from the configuration'
    )

    cmd.add_argument(
        'definition', type=argparse.FileType('r'),
        help='yaml description for trigger'
    )

    cmd.set_defaults(cmd=update_weight_cmd)


def update_weight_cmd(args):
    definition = load_yaml(args.definition)

    sys.stdout.write(
        "Updating weight of '{}' to:\n - {}".format(definition['name'], definition['weight'])
    )

    with connect() as conn:
        conn.autocommit = True

        trigger = Trigger.from_config(definition)

        trigger.update_weight(conn)


def timedelta_to_string(t):
    ret = []

    days = t.days
    num_years = int(days / 365)

    if num_years > 0:
        days -= num_years * 365

        if num_years > 1:
            ret.append('{:d} years'.format(num_years))
        else:
            ret.append('{:d} year'.format(num_years))

    if days > 0:
        if days > 1:
            ret.append('{:d} days'.format(days))
        else:
            ret.append('{:d} day'.format(days))

    seconds = t.seconds
    num_hours = int(seconds / 3600)

    if num_hours > 0:
        seconds -= num_hours * 3600

        if num_hours > 1:
            ret.append('{:d} hours'.format(num_hours))
        else:
            ret.append('{:d} hour'.format(num_hours))

    num_minutes = int(seconds / 60)
    if num_minutes > 0:
        if num_minutes > 1:
            ret.append('{:d} minutes'.format(num_minutes))
        else:
            ret.append('{:d} minute'.format(num_minutes))

    return ' '.join(ret)


def list_cmd(_args):
    query = 'SELECT id, name, granularity, enabled FROM trigger.rule'

    with closing(connect()) as conn:
        conn.autocommit = True

        with closing(conn.cursor()) as cursor:
            cursor.execute(query)

            rows = cursor.fetchall()

    show_rows(
        ['id', 'name', 'granularity', 'enabled'],
        [
            (id_, name, timedelta_to_string(granularity), enabled)
            for id_, name, granularity, enabled in rows
        ]
    )


def setup_create_notifications_parser(subparsers):
    cmd = subparsers.add_parser(
        'create-notifications',
        help='command for executing triggers and creating notifications'
    )

    cmd.add_argument('--trigger', help="name of trigger")

    cmd.add_argument(
        '--timestamp', help="timestamp for which to execute trigger"
    )

    cmd.set_defaults(cmd=execute_trigger_cmd)


def execute_trigger_cmd(args):
    if args.timestamp:
        timestamp = dateutil.parser.parse(args.timestamp)
    else:
        timestamp = None

    with closing(connect()) as conn:
        conn.autocommit = True

        notification_count = Trigger.execute_by_name(conn, args.trigger, timestamp)

    print("Notifications generated: {}".format(notification_count))
