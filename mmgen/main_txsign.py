#!/usr/bin/env python
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2016 Philemon <mmgen-py@yandex.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
mmgen-txsign: Sign a transaction generated by 'mmgen-txcreate'
"""

from mmgen.common import *
from mmgen.tx import *
from mmgen.seed import SeedSource

pnm = g.proj_name

# -w is unneeded - use bitcoin-cli walletdump instead
# -w, --use-wallet-dat  Get keys from a running bitcoind
opts_data = {
	'desc':    'Sign Bitcoin transactions generated by {pnl}-txcreate'.format(pnl=pnm.lower()),
	'usage':   '[opts] <transaction file>... [seed source]...',
	'options': """
-h, --help            Print this help message.
-b, --brain-params=l,p Use seed length 'l' and hash preset 'p' for brain-
                      wallet input.
-d, --outdir=      d  Specify an alternate directory 'd' for output.
-D, --tx-id           Display transaction ID and exit.
-e, --echo-passphrase Print passphrase to screen when typing it.
-i, --in-fmt=      f  Input is from wallet format 'f' (see FMT CODES below).
-H, --hidden-incog-input-params=f,o  Read hidden incognito data from file
                      'f' at offset 'o' (comma-separated).
-O, --old-incog-fmt   Specify old-format incognito input.
-l, --seed-len=    l  Specify wallet seed length of 'l' bits.  This option
                      is required only for brainwallet and incognito inputs
                      with non-standard (< {g.seed_len}-bit) seed lengths.
-p, --hash-preset=p   Use the scrypt hash parameters defined by preset 'p'
                      for password hashing (default: '{g.hash_preset}').
-z, --show-hash-presets Show information on available hash presets.
-k, --keys-from-file=f Provide additional keys for non-{pnm} addresses
-K, --no-keyconv      Force use of internal libraries for address gener-
                      ation, even if 'keyconv' is available.
-M, --mmgen-keys-from-file=f Provide keys for {pnm} addresses in a key-
                      address file (output of '{pnl}-keygen'). Permits
                      online signing without an {pnm} seed source.
                      The key-address file is also used to verify
                      {pnm}-to-BTC mappings, so its checksum should
                      be recorded by the user.
-P, --passwd-file= f  Get {pnm} wallet or bitcoind passphrase from file 'f'
-q, --quiet           Suppress warnings; overwrite files without
                      prompting
-I, --info            Display information about the transaction and exit.
-t, --terse-info      Like '--info', but produce more concise output.
-v, --verbose         Produce more verbose output
""".format(g=g,pnm=pnm,pnl=pnm.lower()),
	'notes': """

Transactions with either {pnm} or non-{pnm} input addresses may be signed.
For non-{pnm} inputs, the bitcoind wallet.dat is used as the key source.
For {pnm} inputs, key data is generated from your seed as with the
{pnl}-addrgen and {pnl}-keygen utilities.

Data for the --from-<what> options will be taken from a file if a second
file is specified on the command line.  Otherwise, the user will be
prompted to enter the data.

In cases of transactions with mixed {pnm} and non-{pnm} inputs, non-{pnm}
keys must be supplied in a separate file (WIF format, one key per line)
using the '--keys-from-file' option.  Alternatively, one may get keys from
a running bitcoind using the '--force-wallet-dat' option.  First import the
required {pnm} keys using 'bitcoind importprivkey'.

For transaction outputs that are {pnm} addresses, {pnm}-to-Bitcoin address
mappings are verified.  Therefore, seed material or a key-address file for
these addresses must be supplied on the command line.

Seed data supplied in files must have the following extensions:
   wallet:      '.{g.wallet_ext}'
   seed:        '.{g.seed_ext}'
   mnemonic:    '.{g.mn_ext}'
   brainwallet: '.{g.brain_ext}'

FMT CODES:
  {f}
""".format(
		f='\n  '.join(SeedSource.format_fmt_codes().splitlines()),
		g=g,pnm=pnm,pnl=pnm.lower()
	)
}

wmsg = {
	'mm2btc_mapping_error': """
{pnm} -> BTC address mappings differ!
From %-18s %s -> %s
From %-18s %s -> %s
""".strip().format(pnm=pnm),
	'removed_dups': """
Removed %s duplicate wif key%s from keylist (also in {pnm} key-address file
""".strip().format(pnm=pnm),
}

def get_seed_for_seed_id(seed_id,infiles,saved_seeds):

	if seed_id in saved_seeds:
		return saved_seeds[seed_id]

	while True:
		if infiles:
			ss = SeedSource(infiles.pop(0),ignore_in_fmt=True)
		elif opt.in_fmt:
			qmsg('Need seed data for Seed ID %s' % seed_id)
			ss = SeedSource()
			msg('User input produced Seed ID %s' % make_chksum_8(seed))
		else:
			die(2,'ERROR: No seed source found for Seed ID: %s' % seed_id)

		saved_seeds[ss.seed.sid] = ss.seed.data

		if ss.seed.sid == seed_id: return ss.seed.data

def generate_keys_for_mmgen_addrs(mmgen_addrs,infiles,saved_seeds):

	seed_ids = set([i[:8] for i in mmgen_addrs])
	vmsg('Need seed%s: %s' % (suf(seed_ids,'k'),' '.join(seed_ids)))
	d = []

	from mmgen.addr import generate_addrs
	for seed_id in seed_ids:
		# Returns only if seed is found
		seed = get_seed_for_seed_id(seed_id,infiles,saved_seeds)
		addr_nums = [int(i[9:]) for i in mmgen_addrs if i[:8] == seed_id]
		opt.gen_what = 'ka'
		ai = generate_addrs(seed,addr_nums,source='txsign')
		d += [('{}:{}'.format(seed_id,e.idx),e.addr,e.wif) for e in ai.addrdata]
	return d

# # function unneeded - use bitcoin-cli walletdump instead
# def sign_tx_with_bitcoind_wallet(c,tx,tx_num_str,keys):
# 	ok = tx.sign(c,tx_num_str,keys) # returns false on failure
# 	if ok:
# 		return ok
# 	else:
# 		msg('Using keys in wallet.dat as per user request')
# 		prompt = 'Enter passphrase for bitcoind wallet: '
# 		while True:
# 			passwd = get_bitcoind_passphrase(prompt)
# 			ret = c.walletpassphrase(passwd, 9999,ret_on_error=True)
# 			if rpc_error(ret):
# 				if rpc_errmsg(ret,'unencrypted wallet, but walletpassphrase was called'):
# 					msg('Wallet is unencrypted'); break
# 			else:
# 				msg('Passphrase OK'); break
#
# 		ok = tx.sign(c,tx_num_str,keys)
#
# 		msg('Locking wallet')
# 		ret = c.walletlock(ret_on_error=True)
# 		if rpc_error(ret):
# 			msg('Failed to lock wallet')
#
# 		return ok
#
def missing_keys_errormsg(addrs):
	Msg("""
A key file must be supplied (or use the '--use-wallet-dat' option)
for the following non-{pnm} address{suf}:\n    {l}""".format(
	pnm=pnm, suf=suf(addrs,'a'), l='\n    '.join(addrs)).strip())

def parse_mmgen_keyaddr_file():
	from mmgen.addr import AddrInfo
	ai = AddrInfo(opt.mmgen_keys_from_file,has_keys=True)
	vmsg('Found %s wif key%s for Seed ID %s' %
			(ai.num_addrs, suf(ai.num_addrs,'k'), ai.seed_id))
	# idx: (0=addr, 1=comment 2=wif) -> mmaddr: (0=addr, 1=wif)
	return dict(
		[('%s:%s'%(ai.seed_id,e.idx), (e.addr,e.wif)) for e in ai.addrdata])

def parse_keylist(key_data):
	fn = opt.keys_from_file
	from mmgen.crypto import mmgen_decrypt_file_maybe
	dec = mmgen_decrypt_file_maybe(fn,'non-{} keylist file'.format(pnm))
	# Key list could be bitcoind dump, so remove first space and everything following
	keys_all = set([line.split()[0] for line in remove_comments(dec.splitlines())]) # DOS-safe
	dmsg(repr(keys_all))
	ka_keys = [d[k][1] for k in key_data['kafile']]
	keys = [k for k in keys_all if k not in ka_keys]
	removed = len(keys_all) - len(keys)
	if removed:
		vmsg(wmsg['removed_dups'] % (removed,suf(removed,'k')))
	addrs = []
	wif2addr_f = get_wif2addr_f()
	for n,k in enumerate(keys,1):
		qmsg_r('\rGenerating addresses from keylist: %s/%s' % (n,len(keys)))
		addrs.append(wif2addr_f(k))
	qmsg('\rGenerated addresses from keylist: %s/%s ' % (n,len(keys)))

	return dict(zip(addrs,keys))

# Check inputs and outputs maps against key-address file, deleting entries:
def check_maps_from_kafile(io_map,desc,kadata,return_keys=False):
	if not kadata: return []
	qmsg('Checking {pnm} -> BTC address mappings for {w}s (from key-address file)'.format(pnm=pnm,w=desc))
	ret = []
	for k in io_map.keys():
		if k in kadata:
			if kadata[k][0] == io_map[k]:
				del io_map[k]
				ret += [kadata[k][1]]
			else:
				kl,il = 'key-address file:','tx file:'
				die(2,wmsg['mm2btc_mapping_error']%(kl,k,kadata[k][0],il,k,io_map[k]))
	if ret: vmsg('Removed %s address%s from %ss map' % (len(ret),suf(ret,'a'),desc))
	if return_keys:
		vmsg('Added %s wif key%s from %ss map' % (len(ret),suf(ret,'k'),desc))
		return ret

# Check inputs and outputs maps against values generated from seeds
def check_maps_from_seeds(io_map,desc,infiles,saved_seeds,return_keys=False):

	if not io_map: return []
	qmsg('Checking {pnm} -> BTC address mappings for {w}s (from seed(s))'.format(
				pnm=pnm,w=desc))
	d = generate_keys_for_mmgen_addrs(io_map.keys(),infiles,saved_seeds)
#	0=mmaddr 1=addr 2=wif
	m = dict([(e[0],e[1]) for e in d])
	for a,b in zip(sorted(m),sorted(io_map)):
		if a != b:
			al,bl = 'generated seed:','tx file:'
			die(3,wmsg['mm2btc_mapping_error'] % (al,a,m[a],bl,b,io_map[b]))
	if return_keys:
		vmsg('Added %s wif key%s from seeds' % (len(d),suf(d,'k')))
		return [e[2] for e in d]

def get_keys_from_keylist(kldata,addrs):
	ret = []
	for addr in addrs[:]:
		if addr in kldata:
			ret += [kldata[addr]]
			addrs.remove(addr)
	vmsg('Added %s wif key%s from user-supplied keylist' %
			(len(ret),suf(ret,'k')))
	return ret

# main(): execution begins here

infiles = opts.init(opts_data,add_opts=['b16'])

if not infiles: opts.usage()
for i in infiles: check_infile(i)

c = bitcoin_connection()

saved_seeds = {}
tx_files   = [i for i in infiles if get_extension(i) == g.rawtx_ext]
seed_files = [i for i in infiles if get_extension(i) in g.seedfile_exts]

if not tx_files:
	die(1,'You must specify a raw transaction file!')
if not (seed_files or opt.mmgen_keys_from_file or opt.keys_from_file or opt.use_wallet_dat):
	die(1,'You must specify a seed or key source!')

if not opt.info and not opt.terse_info:
	do_license_msg(immed=True)

key_data = { 'kafile':{}, 'klfile':{} }
if opt.mmgen_keys_from_file:
	key_data['kafile'] = parse_mmgen_keyaddr_file() or {}
if opt.keys_from_file:
	key_data['klfile'] = parse_keylist(key_data) or {}

tx_num_str = ''
for tx_num,tx_file in enumerate(tx_files,1):
	if len(tx_files) > 1:
		msg('\nTransaction #%s of %s:' % (tx_num,len(tx_files)))
		tx_num_str = ' #%s' % tx_num

	tx = MMGenTX(tx_file)

	if tx.check_signed(c):
		die(1,'Transaction is already signed!')

	vmsg("Successfully opened transaction file '%s'" % tx_file)

	if opt.tx_id: die(0,tx.txid)

	if opt.info or opt.terse_info:
		tx.view(pause=False,terse=opt.terse_info)
		sys.exit()

	tx.view_with_prompt('View data for transaction%s?' % tx_num_str)

	# Start
	other_addrs = list(set([i['address'] for i in tx.inputs if not i['mmid']]))

	# should remove all elements from other_addrs
	keys = get_keys_from_keylist(key_data['klfile'],other_addrs)

	if other_addrs and not opt.use_wallet_dat:
		missing_keys_errormsg(other_addrs)
		sys.exit(2)

	imap = dict([(i['mmid'],i['address']) for i in tx.inputs if i['mmid']])
	omap = dict([(tx.outputs[k][1],k) for k in tx.outputs if len(tx.outputs[k]) > 1])
	sids = set([i[:8] for i in imap])

	keys += check_maps_from_kafile(imap,'input',key_data['kafile'],True)
	check_maps_from_kafile(omap,'output',key_data['kafile'])

	keys += check_maps_from_seeds(imap,'input',seed_files,saved_seeds,True)
	check_maps_from_seeds(omap,'output',seed_files,saved_seeds)

	extra_sids = set(saved_seeds) - sids
	if extra_sids:
		msg('Unused Seed ID%s: %s' %
			(suf(extra_sids,'k'),' '.join(extra_sids)))

# 	if opt.use_wallet_dat:
# 		ok = sign_tx_with_bitcoind_wallet(c,tx,tx_num_str,keys)
# 	else:
	ok = tx.sign(c,tx_num_str,keys)

	if ok:
		tx.add_comment()   # edits an existing comment
		tx.write_to_file(ask_write_default_yes=True,add_desc=tx_num_str)
	else:
		die(3,'failed\nSome keys were missing.  Transaction %scould not be signed.' % tx_num_str)
