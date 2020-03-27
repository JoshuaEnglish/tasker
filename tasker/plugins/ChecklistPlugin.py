"""
Checklist Plugin

Manages complex checklists that the workflow plugin cannot handle well

Created on 2020-03-24
"""

import logging
import pathlib
import copy
import datetime
import argparse
import xml.etree.ElementTree as ET

import basetaskerplugin
import minioncmd
import lister

long_term_plans = """
Create method for archiving fully completed checklist but still making them
available to the system.
"""
# constants for return values
GOOD = 0
BAD = 1
ERROR = -1

HERE = pathlib.Path(__file__).resolve().parent
CHECKLISTS = HERE / 'checklists'



class ChecklistLib(object):
    def __init__(self, directory):
        self._log = logging.getLogger('checklistlib')
        self._log.info('creating ChecklistLib')
        self.directory = pathlib.Path(directory)
        if not self.directory.exists():
            self.directory.mkdir()
        self.checklists = {}
        self.paths = {}
        for path in self.directory.glob('*.xml'):
            node = ET.parse(path)
            root = node.getroot()
            self.checklists[path.stem] = root
            self.paths[path.stem] = path.resolve()
            node.write(self.directory / 'backup' / f"{path.stem}.bak",
                       encoding='utf-8',
                       xml_declaration=True)

    def new_template(self, name):
        """creates a default empty checklist file"""
        if name in self.checklists:
            msg = f'Checklist for {name} already exists'
            self._log.error(msg)
            return ERROR, msg
        ch = ET.Element('checklist')
        tm = ET.SubElement(ch, '_template', name=name, version="1.0")
        hd = ET.SubElement(tm, 'header')
        ET.SubElement(hd, 'input', idsource='true', key='thing',
                      name='thing')
        gr = ET.SubElement(tm, 'group', id='firstgroup',
                           name='First Group')
        sg = ET.SubElement(gr, 'subgroup', id='sb', name='First Subgroup')
        act = ET.SubElement(sg, 'action', completed='false', dated='false')
        act.text = 'First Action'
        self.checklists[name] = ch
        self.paths[name] = self.directory / f'{name}.xml'
        self._write_checklist(name)

    def create_instance(self, checklistname, **kwargs):
        """create_instance(checklistname, **kwargs)
        Create a new instance of a checklist
        """
        self._log.info('Trying to create %s instance', checklistname)
        if checklistname not in self.checklists:
            self._log.error('No checklist named %s', checklistname)
            return BAD, "No checklist name %s" % checklistname
        this = self.checklists[checklistname]
        template = this.find('_template')
        header = template.find('header')
        inputs = header.findall('input')
        emptykeys = [i.get('key') for i in inputs]
        candidate = copy.deepcopy(template)
        candidate.tag = 'instance'
        newheader = candidate.find('header')
        for key, value in kwargs.items():
            if key in emptykeys:
                self._log.debug('setting header value for %s: %s', key, value)
                newheader.find(f'input[@key="{key}"]').text = value
                emptykeys.remove(key)
            else:
                msg = f"Checklist {checklistname} has no header key {key}"
                self._log.error(msg)
                return BAD, msg
        if emptykeys:
            self._log.error('Checklist header missing: %s', emptykeys)
            return BAD, f"Checklist header missng {emptykeys}"
        # set the candidate id to the appropriate thing
        idnode = newheader.find('input[@idsource="true"]')
        newid = ''.join(idnode.text.split())
        self._log.debug('Setting new candidate id to %s', newid)
        candidate.set('id', ''.join(newid))
        self._log.debug('Checking for duplicate IDs')
        current_ids = [i.get('id') for i in this.findall('instance')]
        if newid in current_ids:
            msg = 'Checklist id %s already exists', newid
            self._log.error(msg)
            return BAD, msg
        this.append(candidate)
        self._write_checklist(checklistname)
        msg = f"Created {checklistname} instance for {newid}"
        self._log.info(msg)
        return True, msg

    def _write_checklist(self, checklistname):
        self._log.info('Writing %s to file', checklistname)
        with open(self.paths[checklistname], 'w') as f:
            f.write(ET.tostring(self.checklists[checklistname]).decode())

    def list_instances(self, checklistname):
        """list_instances(name)
        Returns a list of IDs for the instances of a given checklist
        """
        self._log.info('listing instances of %s', checklistname)
        if checklistname not in self.checklists:
            msg = 'No checklist named %s', checklistname
            self._log.error(msg)
            return ERROR

        this = self.checklists[checklistname]
        return [i.get('id') for i in this.findall('instance')]

    def get_open_subgroups(self, checklistname, checklistid):
        """get_open_subgroups(checklistname, checklistid)
        Return actual nodes of subgroups that are not fully marked
        as complete.
        """
        self._log.info('Listing open subgroups of %s', checklistid)
        if checklistname not in self.checklists:
            self._log.error('No checklist named %s', checklistname)
            return None
        this = self.checklists[checklistname].find(
            f'instance[@id="{checklistid}"]')
        if this is None:
            self._log.error('No %s checklist instance for %s',
                          checklistname, checklistid)
            return False

        return [group for group in this.iterfind('group/subgroup')
                if not self._is_subgroup_complete(group)]

    def _is_subgroup_complete(self, node):
        """Return true if all the actions in a node are complete"""
        self._log.debug('Checking if %s is complete', node)
        completed = True
        for action in node.findall('action'):
            if action.get('completed', 'false') == 'false':
                completed = False
        for inode in node.findall('input'):
            if inode.text is None:
                completed = False

        return completed

    def _get_subgroup(self, checklistname, instanceid, subgroupid):
        """return the node for a subgroup. Return None if no
        subgroup is found"""

        self._log.debug('Getting %s subgroups of %s (%s)',
                      subgroupid, instanceid, checklistname)
        if checklistname not in self.checklists:
            self._log.error('No checklist named %s', checklistname)
            return None
        this = self.checklists[checklistname].find(
            f'instance[@id="{instanceid}"]')
        if this is None:
            self._log.error('No %s checklist instance for %s',
                          checklistname, instanceid)
            return None

        res = this.find(f'group/subgroup[@id="{subgroupid}"]')
        if res is None:
            self._log.error('No subgroup under % with id %s',
                          instanceid, subgroupid)
        return res

    def list_inputs(self, checklistname, instance, subgroup):
        subgroup = self._get_subgroup(checklistname, instance, subgroup)
        if subgroup is None:
            return None
        res = []
        for idx, node in enumerate(subgroup.findall('input'), 1):
            res.append((idx,
                        node.get('name'),
                        node.text))
        return res

    def fill_input(self, checklistname, instance, subgroup, number, value):
        """fill_input(checklist, instance, subgroup, number, value)
        Adds data to the system.
        """
        self._log.info(f'Filling {value} into {subgroup} for {instance}')
        subgroupnode = self._get_subgroup(checklistname, instance, subgroup)
        if subgroupnode is None:
            msg = f"No subgroup {subgroup} in {instance} of {checklistname}"
            return ERROR, msg
        inputs = {}
        for idx, node in enumerate(subgroupnode.findall('input'), 1):
            inputs[idx] = node
        if number not in inputs:
            msg = f'No input number {number} in {subgroup}'
            self._log.error(msg)
            return ERROR, msg
        inputs[number].text = value
        self._log.debug('Input %s recorded', value)
        self._write_checklist(checklistname)
        return GOOD, 'Input recorded'

    def complete_action(self, checklistname, instance, subgroup, number,
                        value=None):
        """complete_action(checklist, instance, subgroup, idx [,value])
        Marks a particular action complete.
        If the action is dated, must pass the date of the action.
        """
        value = value or 'true'
        self._log.info('Marking %s:%d complete in %s (%s)',
                     subgroup, number, instance, checklistname)
        subgroup = self._get_subgroup(checklistname, instance, subgroup)
        if subgroup is None:
            msg = f"No subgroup {subgroup} in {instance} of {checklistname}"
            return ERROR, msg
        actions = {}
        for idx, node in enumerate(subgroup.findall('action'), 1):
            actions[idx] = node
        if number not in actions:
            msg = 'No action number {number} in {subgroup}'
            self._log.error(msg)
            return ERROR, msg
        if node.get('dated', False) == 'true':
            try:
                datetime.date.fromisoformat(value)
                actions[number].set('completed', value)
            except ValueError:
                msg = 'Action is dated and must have valid date'
                self._log.error(msg)
                return ERROR, msg
        else:
            actions[number].set('completed', 'true')
        self._log.debug('Mark successful')
        self._write_checklist(checklistname)
        return GOOD, 'Marked complete'

    def complete_all_actions(self, checklistname, instance):
        '''mark all items complete. dated items are marked complet
        to the day. Will query for any unanswered inputs'''
        pass


class ChecklistCLI(minioncmd.MinionCmd):
    prompt = 'checklist>'
    minion_header = 'Other subcommands (type <subcommand> help)'
    doc_leader = """Checklist Help

    Store complex repetitive tasks without cluttering the task list.
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 checklib=None):
        super().__init__('checklist',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)
        self.checklib = checklib

    def do_new(self, text):
        """creates a new checklist skeleton. User will need to manually edit"""
        self.checklib.new_template(text)
        print(f"Checklist {text} created")

    def do_list(self, text):
        """Usage: list

        List current checklists"""
        for key in self.checklib.checklists:
            print(key)

    def do_instances(self, text):
        """list instances of a checklist"""
        for idx, name in enumerate(
                self.checklib.list_instances(text.strip()), 1):
            print(idx, name)

    def do_create(self, text):
        '''creates a new instance of a checklist'''
        this = self.checklib.checklists[text.strip()]
        if this is None:
            print(f'No checklist for {text} found')
            return None
        header = this.find('_template/header')
        data = {}
        idx = None
        for query in header.findall('input'):
            answer = input(f"{query.get('name')}: ")
            if query.get('idsource', 'false') == 'true':
                idx = answer
            data[query.get('key')] = answer
        self.checklib.create_instance(text.strip(), **data)
        if idx is None:
            print('Done but probably broken')
        else:
            print('Created checklist for', idx)

    def do_opentasks(self, text):
        '''Usage: opentasks CHECKLIST INSTANCE
        List open tasks (collections of actions) for an
        instance of a checklist. Also notes if the task has separate
        inputs or an information block
        '''
        clist, inst, *junk = text.split(maxsplit=2)
        headers = ['ID', 'Name', 'Inputs', 'Info']
        stuff = [(node.get('id'), node.get('name'),
                  str(node.find('input') is not None),
                  str(node.find('information') is not None))
                 for node in self.checklib.get_open_subgroups(clist, inst)]
        lister.print_list(stuff, headers)

    def do_actions(self, text):
        """Usage actions checklist instance subgroupid
        List actions in a particular subgroup
        """
        try:
            clist, inst, sgid, *junk = text.split(maxsplit=3)
        except ValueError as E:
            print(E)
            return False
        subgroup = self.checklib._get_subgroup(clist, inst, sgid)
        if subgroup is None:
            print("No subgroup found")
            return False
        res = []
        for idx, node in enumerate(subgroup.findall('action'), 1):
            res.append([str(idx),
                        node.text,
                        node.get('completed'),
                        node.get('dated', 'false')])
        lister.print_list(res, '# Action Completed Dated'.split())

    def do_getinfo(self, text):
        """Usage getinfo checklist instance subgroupid
        List information about a task."""
        try:
            clist, inst, sgid, *junk = text.split(maxsplit=3)
        except ValueError as E:
            print(E)
            return False
        subgroup = self.checklib._get_subgroup(clist, inst, sgid)
        if subgroup is None:
            print("No subgroup found")
            return False
        if subgroup.find('information') is None:
            print('No information block')
            return False
        for info in subgroup.findall('information'):
            print(info.text)

    def do_inputs(self, text):
        """Usage: inputs checklist instance subgroupid
        Lists inputs related to a task."""
        clist, inst, sgid, *junk = text.split(maxsplit=3)
        header = '# Input Value'.split()
        lister.print_list(
            [(str(i), n, str(t)) for i,n,t in
              self.checklib.list_inputs(clist, inst, sgid)],
            header)

    def do_fill(self, text):
        """Usage: fill checklist instance subgroup number value"""
        clist, inst, sgid, num, *value = text.split(maxsplit=4)
        res, msg = self.checklib.fill_input(
            clist, inst, sgid, int(num), ''.join(value))
        if res:
            print(res, msg)
        else:
            print(msg)

    def do_do(self, text):
        """Usage: do checklist instance subgroupid number [,date]
        Mark a particular action complete. Will default to today's date
        if date is required but no date given"""
        clist, inst, sgid, num, *stuff = text.split(maxsplit=4)
        if len(stuff) == 0:
            stuff.append(datetime.date.today().isoformat())
        try:
            datetime.date.fromisoformat(stuff[0])
            this_date =stuff[0]
        except (ValueError, TypeError):
            this_date = datetime.date.today().isoformat()
        res, msg = self.checklib.complete_action(
            clist,
            inst,
            sgid,
            int(num),
            this_date)
        if res:
            print(res, msg)
        else:
            print(msg)
        """subgroup = self.checklib._get_subgroup(clist, inst, sgid)
        if subgroup is None:
            print('No subgroup found')
            return False
        res = {}
        for idx, node in enumerate(subgroup.findall('action'), 1):
            res[str(idx)] = node
        if num not in res:
            print("No action number in subgroup found")
            return False
        res[num].set('completed', this_date)
        self.checklib._write_checklist(clist)"""


class ChecklistPlugin(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        self._log.debug('Activating Checklist')
        if not self.hasConfigOption('directory'):
            self._log.debug('Setting Checklist directory to default')
            self.setConfigOption('directory', str(CHECKLISTS))

        self.cli_name = 'checklist'
        self.checklib = ChecklistLib(self.getConfigOption('directory'))

        self.cli = ChecklistCLI(checklib=self.checklib)

        parser = self.parser = argparse.ArgumentParser('checklist')
        checklist_command = parser.add_subparsers(title='Checklist Commands',
                                                  dest='subcommand',
                                                  metavar='')
        checklist_command.add_parser(
            'list', help='Lists current checklists')

        i = checklist_command.add_parser(
            'instances', help='Lists instances of a checklist')
        i.add_argument('checklist', help='the name of the checklist')

        c = checklist_command.add_parser(
            'create', help='Create a new instance of a checklist')
        c.add_argument('checklist', help='the name of checklist to create')

        self.parsers = {
            parser: 'Checklists'}

        super().activate()


if __name__ == '__main__':
    chlib = ChecklistLib(CHECKLISTS)
    print(chlib.list_instances('newhire'))
    for subgroup in chlib.get_open_subgroups('newhire', 'ReymundoGuerrero'):
        print(subgroup.get('id'), subgroup.get('name'))
    print(chlib.list_actions('newhire', 'ReymundoGuerrero', 'dw'))
    print(chlib.get_open_subgroups('newhire', 'ReymundoGuerrero'))
    print(chlib.list_inputs('newhire', 'ReymundoGuerrero', 'sfdc'))
    p = ChecklistPlugin()
    print(p)
    print(p.cli)
    chlib.create_template('termination')
