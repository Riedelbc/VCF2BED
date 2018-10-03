#!/usr/bin/env python

import argparse, sys
import math, time, re
from collections import Counter
from argparse import RawTextHelpFormatter

__author__ = "Colby Chiang (cc2qe@virginia.edu)"
__version__ = "$Revision: 0.0.1 $"
__date__ = "$Date: 2015-09-27 09:31 $"

# --------------------------------------
# define functions

def get_args():
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description="\
vcfToBed.py\n\
author: " + __author__ + "\n\
version: " + __version__ + "\n\
description: convert SV VCF to BED file")
    parser.add_argument(metavar='vcf', dest='input_vcf', nargs='?', type=argparse.FileType('r'), default=None, help='VCF input (default: stdin)')
    parser.add_argument('-m', dest='inv_multi', action='store_true', default=None, help='represent INV as multi line')
    parser.add_argument('-e', dest='event_id', action='store_true', default=None, help='for BND variants, use EVENT field from VCF (if available) for column 4 of BED file')
    parser.add_argument('-b', '--bnd_span', dest='bnd_span', action='store_true', default=None, help='for BND variants, print BED interval of variant\'s span and add BND_DETAIL to INFO field (sloppily)')

    # parse the arguments
    args = parser.parse_args()

    # if no input, check if part of pipe and if so, read stdin.
    if args.input_vcf == None:
        if sys.stdin.isatty():
            parser.print_help()
            exit(1)
        else:
            args.input_vcf = sys.stdin
    # send back the user input
    return args

# primary function
def vcf_to_bed(inv_multi, event_id, bnd_span, vcf_file):
    # read input VCF
    for line in vcf_file:
        if line[0] == '#':
            if line[:13] == '##fileformat=':
                print '##fileformat=BEDv0.2'
                continue
            if line[1] != '#':
                vcf_samples = line.rstrip().split('\t')[9:]
                print '\t'.join(['#CHROM',
                                'POS_START',
                                'POS_END',
                                'ID',
                                'REF',
                                'ALT',
                                'QUAL',
                                'FILTER',
                                'INFO',
                                'FORMAT'] +
                                vcf_samples)
                continue
                                
            print line.rstrip()
            continue

        v = line.rstrip().split('\t')

        info_split = [i.split('=') for i in v[7].split(';')]
        for i in info_split:
            if len(i) == 1:
                i.append(True)
        info = dict(info_split)

        bed_list = []

        if 'SVTYPE' not in info:
            chrom = v[0]
            start = int(v[1]) - 1
            end = start + len(v[3])
            event = v[2]
            bed = [chrom, start, end, event]
            bed_list.append(bed)

        elif info['SVTYPE'] == 'BND':
            chrom = v[0]
            pos = int(v[1])
            start = int(v[1]) - 1
            end = int(v[1])
            if event_id:
                event = info['EVENT']
            else:
                event = v[2]

            if bnd_span:
                distance_threshold = 1e6
                alt = v[4]
                if "[" in alt or "]" in alt: # BND
                    orient = ""
                    alt_coord = re.findall('[\[\]]([^\[\]]*)[\[\]]', alt)[0].split(':')
                    alt_chrom = alt_coord[0]
                    alt_pos = int(alt_coord[1])
                    if chrom != alt_chrom:
                        interchrom = True
                        distance = None
                    else:
                        interchrom = False
                        distance = abs(alt_pos - pos)
                        start = pos
                        end = alt_pos

                    if alt.startswith('['):
                        orient = "INV"
                    elif alt.startswith(']'):
                        if pos > alt_pos:
                            orient = "DEL"
                        else:
                            orient = "DUP"
                    elif alt.endswith('['):
                        if pos > alt_pos:
                            orient = "DUP"
                        else:
                            orient = "DEL"
                    elif alt.endswith(']'):
                        orient = "INV"
                    bnd_detail = "BND"
                    if interchrom:
                        bnd_detail = "INTER_" + bnd_detail
                    else:
                        if distance > distance_threshold:
                            bnd_detail = "DISTANT_" + bnd_detail + "_" + orient
                        else:
                            bnd_detail = "LOCAL_" + bnd_detail + "_" + orient

                # add the BND_DETAIL to the info field
                # note: this is done in a sketchy and illegal way. Not added to the
                # header and it doesn't check whether the field already exists.
                info['BND_DETAIL'] = bnd_detail
                v[7] = v[7] + ';BND_DETAIL=' + bnd_detail

            bed = [chrom, min(start, end), max(start, end), event]
            bed_list.append(bed)

        elif info['SVTYPE'] == 'INV' and inv_multi:
            chrom_1 = v[0]
            start_1 = int(v[1])
            end_1 = int(v[1]) + 1
            event_1 = v[2]
            bed_1 = [chrom_1, start_1, end_1, event_1]

            chrom_2 = v[0]
            start_2 = int(info['END']) - 1
            end_2 = int(info['END'])
            event_2 = v[2]
            bed_2 = [chrom_2, start_2, end_2, event_2]

            bed_list.append(bed_1)
            bed_list.append(bed_2)
            
        else:
            chrom = v[0]
            if 'END' in info:
                start = int(v[1])
                end = int(info['END'])
            else:
                start = int(v[1]) - 1
                end = int(v[1])
            event = v[2]
            bed = [chrom, start, end, event]
            bed_list.append(bed)

        for b in bed_list:
            print '\t'.join(map(str, b)) + '\t' +  '\t'.join(v[3:])
    
    return

# --------------------------------------
# main function

def main():
    # parse the command line args
    args = get_args()

    # call primary function
    vcf_to_bed(args.inv_multi, args.event_id, args.bnd_span, args.input_vcf)

    # close the files
    args.input_vcf.close()

# initialize the script
if __name__ == '__main__':
    try:
        sys.exit(main())
    except IOError, e:
        if e.errno != 32:  # ignore SIGPIPE
            raise 