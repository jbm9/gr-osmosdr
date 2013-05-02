#!/usr/bin/env python
#
# Copyright 2008,2009,2011,2012 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

SAMP_RATE_KEY = 'samp_rate'
LINK_RATE_KEY = 'link_rate'
GAIN_KEY = 'gain'
IF_GAIN_KEY = 'if_gain'
BWIDTH_KEY = 'bwidth'
TX_FREQ_KEY = 'tx_freq'
FREQ_CORR_KEY = 'freq_corr'
AMPLITUDE_KEY = 'amplitude'
AMPL_RANGE_KEY = 'ampl_range'
WAVEFORM_FREQ_KEY = 'waveform_freq'
WAVEFORM_OFFSET_KEY = 'waveform_offset'
WAVEFORM2_FREQ_KEY = 'waveform2_freq'
FREQ_RANGE_KEY = 'freq_range'
GAIN_RANGE_KEY = 'gain_range'
IF_GAIN_RANGE_KEY = 'if_gain_range'
BWIDTH_RANGE_KEY = 'bwidth_range'
TYPE_KEY = 'type'

def setter(ps, key, val): ps[key] = val

import osmosdr
from gnuradio import gr, gru, eng_notation
from gnuradio.gr.pubsub import pubsub
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math

n2s = eng_notation.num_to_str

waveforms = { gr.GR_SIN_WAVE   : "Complex Sinusoid",
              gr.GR_CONST_WAVE : "Constant",
              gr.GR_GAUSSIAN   : "Gaussian Noise",
              gr.GR_UNIFORM    : "Uniform Noise",
              "2tone"          : "Two Tone",
              "sweep"          : "Sweep" }

#
# GUI-unaware GNU Radio flowgraph.  This may be used either with command
# line applications or GUI applications.
#
class top_block(gr.top_block, pubsub):
    def __init__(self, options, args):
        gr.top_block.__init__(self)
        pubsub.__init__(self)
        self._verbose = options.verbose

        #initialize values from options
        self._setup_osmosdr(options)
        self[SAMP_RATE_KEY] = options.samp_rate
        self[TX_FREQ_KEY] = options.tx_freq
        self[FREQ_CORR_KEY] = options.freq_corr
        self[AMPLITUDE_KEY] = options.amplitude
        self[WAVEFORM_FREQ_KEY] = options.waveform_freq
        self[WAVEFORM_OFFSET_KEY] = options.offset
        self[WAVEFORM2_FREQ_KEY] = options.waveform2_freq

        #subscribe set methods
        self.subscribe(SAMP_RATE_KEY, self.set_samp_rate)
        self.subscribe(GAIN_KEY, self.set_gain)
        self.subscribe(IF_GAIN_KEY, self.set_if_gain)
        self.subscribe(BWIDTH_KEY, self.set_bandwidth)
        self.subscribe(TX_FREQ_KEY, self.set_freq)
        self.subscribe(FREQ_CORR_KEY, self.set_freq_corr)
        self.subscribe(AMPLITUDE_KEY, self.set_amplitude)
        self.subscribe(WAVEFORM_FREQ_KEY, self.set_waveform_freq)
        self.subscribe(WAVEFORM2_FREQ_KEY, self.set_waveform2_freq)
        self.subscribe(TYPE_KEY, self.set_waveform)

        #force update on pubsub keys
        for key in (SAMP_RATE_KEY, GAIN_KEY, IF_GAIN_KEY, BWIDTH_KEY,
                    TX_FREQ_KEY, FREQ_CORR_KEY, AMPLITUDE_KEY,
                    WAVEFORM_FREQ_KEY, WAVEFORM_OFFSET_KEY, WAVEFORM2_FREQ_KEY):
#            print "key: ", key, "=", self[key]
            self[key] = self[key]
        self[TYPE_KEY] = options.type #set type last

    def _setup_osmosdr(self, options):
        self._sink = osmosdr.sink_c(options.args)
        self._sink.set_sample_rate(options.samp_rate)

        # Set the gain from options
        if(options.gain):
            self._sink.set_gain(options.gain)

        # Set the antenna
        if(options.antenna):
            self._sink.set_antenna(options.antenna, 0)

        self.publish(FREQ_RANGE_KEY, self._sink.get_freq_range)
        self.publish(GAIN_RANGE_KEY, self._get_rf_gain_range)
        self.publish(IF_GAIN_RANGE_KEY, self._get_if_gain_range)
        self.publish(BWIDTH_RANGE_KEY, self._sink.get_bandwidth_range)
        self.publish(GAIN_KEY, self._get_rf_gain)
        self.publish(IF_GAIN_KEY, self._get_if_gain)
        self.publish(BWIDTH_KEY, self._sink.get_bandwidth)

    def _get_rf_gain_range(self):
        return self._sink.get_gain_range("RF")

    def _get_if_gain_range(self):
        return self._sink.get_gain_range("IF")

    def _get_rf_gain(self):
        return self._sink.get_gain("RF")

    def _get_if_gain(self):
        return self._sink.get_gain("IF")

    def _set_tx_amplitude(self, ampl):
        """
        Sets the transmit amplitude
        @param ampl the amplitude or None for automatic
        """
        ampl_range = self[AMPL_RANGE_KEY]
        if ampl is None:
            ampl = (ampl_range[1] - ampl_range[0])*0.3 + ampl_range[0]
        self[AMPLITUDE_KEY] = max(ampl_range[0], min(ampl, ampl_range[1]))

    def set_samp_rate(self, sr):
        self._sink.set_sample_rate(sr)
        sr = self._sink.get_sample_rate()

        if self[TYPE_KEY] in (gr.GR_SIN_WAVE, gr.GR_CONST_WAVE):
            self._src.set_sampling_freq(self[SAMP_RATE_KEY])
        elif self[TYPE_KEY] == "2tone":
            self._src1.set_sampling_freq(self[SAMP_RATE_KEY])
            self._src2.set_sampling_freq(self[SAMP_RATE_KEY])
        elif self[TYPE_KEY] == "sweep":
            self._src1.set_sampling_freq(self[SAMP_RATE_KEY])
            self._src2.set_sampling_freq(self[WAVEFORM_FREQ_KEY]*2*math.pi/self[SAMP_RATE_KEY])
        else:
            return True # Waveform not yet set

        if self._verbose:
            print "Set sample rate to:", sr

        return True

    def set_gain(self, gain):
        if gain is None:
            g = self[GAIN_RANGE_KEY]
            gain = float(g.start()+g.stop())/2
            if self._verbose:
                print "Using auto-calculated mid-point RF gain"
            self[GAIN_KEY] = gain
            return
        gain = self._sink.set_gain(gain, "RF")
        if self._verbose:
            print "Set RF gain to:", gain

    def set_if_gain(self, gain):
        if gain is None:
            g = self[IF_GAIN_RANGE_KEY]
            gain = float(g.start()+g.stop())/2
            if self._verbose:
                print "Using auto-calculated mid-point IF gain"
            self[IF_GAIN_KEY] = gain
            return
        gain = self._sink.set_gain(gain, "IF")
        if self._verbose:
            print "Set IF gain to:", gain

    def set_bandwidth(self, bw):
        bw = self._sink.set_bandwidth(bw)
        if self._verbose:
            print "Set bandwidth to:", bw

    def set_freq(self, target_freq):

        if target_freq is None:
            f = self[FREQ_RANGE_KEY]
            target_freq = float(f.start()+f.stop())/2.0
            if self._verbose:
                print "Using auto-calculated mid-point frequency"
            self[TX_FREQ_KEY] = target_freq
            return

        tr = self._sink.set_center_freq(target_freq)
        if tr is not None:
            self._freq = tr
            if self._verbose:
                print "Set center frequency to", tr
        elif self._verbose:
            print "Failed to set freq."
        return tr

    def set_freq_corr(self, ppm):
        if ppm is None:
            if self._verbose:
                print "Setting freq corrrection to 0"
            self[FREQ_CORR_KEY] = 0
            return

        ppm = self._sink.set_freq_corr(ppm)
        if self._verbose:
            print "Set freq correction to:", ppm

    def set_waveform_freq(self, freq):
        if self[TYPE_KEY] == gr.GR_SIN_WAVE:
            self._src.set_frequency(freq)
        elif self[TYPE_KEY] == "2tone":
            self._src1.set_frequency(freq)
        elif self[TYPE_KEY] == 'sweep':
            #there is no set sensitivity, redo fg
            self[TYPE_KEY] = self[TYPE_KEY]
        return True

    def set_waveform2_freq(self, freq):
        if freq is None:
            self[WAVEFORM2_FREQ_KEY] = -self[WAVEFORM_FREQ_KEY]
            return
        if self[TYPE_KEY] == "2tone":
            self._src2.set_frequency(freq)
        elif self[TYPE_KEY] == "sweep":
            self._src1.set_frequency(freq)
        return True

    def set_waveform(self, type):
        self.lock()
        self.disconnect_all()
        if type == gr.GR_SIN_WAVE or type == gr.GR_CONST_WAVE:
            self._src = gr.sig_source_c(self[SAMP_RATE_KEY],      # Sample rate
                                        type,                # Waveform type
                                        self[WAVEFORM_FREQ_KEY], # Waveform frequency
                                        self[AMPLITUDE_KEY],     # Waveform amplitude
                                        self[WAVEFORM_OFFSET_KEY])        # Waveform offset
        elif type == gr.GR_GAUSSIAN or type == gr.GR_UNIFORM:
            self._src = gr.noise_source_c(type, self[AMPLITUDE_KEY])
        elif type == "2tone":
            self._src1 = gr.sig_source_c(self[SAMP_RATE_KEY],
                                         gr.GR_SIN_WAVE,
                                         self[WAVEFORM_FREQ_KEY],
                                         self[AMPLITUDE_KEY]/2.0,
                                         0)
            if(self[WAVEFORM2_FREQ_KEY] is None):
                self[WAVEFORM2_FREQ_KEY] = -self[WAVEFORM_FREQ_KEY]

            self._src2 = gr.sig_source_c(self[SAMP_RATE_KEY],
                                         gr.GR_SIN_WAVE,
                                         self[WAVEFORM2_FREQ_KEY],
                                         self[AMPLITUDE_KEY]/2.0,
                                         0)
            self._src = gr.add_cc()
            self.connect(self._src1,(self._src,0))
            self.connect(self._src2,(self._src,1))
        elif type == "sweep":
            # rf freq is center frequency
            # waveform_freq is total swept width
            # waveform2_freq is sweep rate
            # will sweep from (rf_freq-waveform_freq/2) to (rf_freq+waveform_freq/2)
            if self[WAVEFORM2_FREQ_KEY] is None:
                self[WAVEFORM2_FREQ_KEY] = 0.1

            self._src1 = gr.sig_source_f(self[SAMP_RATE_KEY],
                                         gr.GR_TRI_WAVE,
                                         self[WAVEFORM2_FREQ_KEY],
                                         1.0,
                                         -0.5)
            self._src2 = gr.frequency_modulator_fc(self[WAVEFORM_FREQ_KEY]*2*math.pi/self[SAMP_RATE_KEY])
            self._src = gr.multiply_const_cc(self[AMPLITUDE_KEY])
            self.connect(self._src1,self._src2,self._src)
        else:
            raise RuntimeError("Unknown waveform type")

        self.connect(self._src, self._sink)
        self.unlock()

        if self._verbose:
            print "Set baseband modulation to:", waveforms[type]
            if type == gr.GR_SIN_WAVE:
                print "Modulation frequency: %sHz" % (n2s(self[WAVEFORM_FREQ_KEY]),)
                print "Initial phase:", self[WAVEFORM_OFFSET_KEY]
            elif type == "2tone":
                print "Tone 1: %sHz" % (n2s(self[WAVEFORM_FREQ_KEY]),)
                print "Tone 2: %sHz" % (n2s(self[WAVEFORM2_FREQ_KEY]),)
            elif type == "sweep":
                print "Sweeping across %sHz to %sHz" % (n2s(-self[WAVEFORM_FREQ_KEY]/2.0),n2s(self[WAVEFORM_FREQ_KEY]/2.0))
                print "Sweep rate: %sHz" % (n2s(self[WAVEFORM2_FREQ_KEY]),)
            print "TX amplitude:", self[AMPLITUDE_KEY]


    def set_amplitude(self, amplitude):
        if amplitude < 0.0 or amplitude > 1.0:
            if self._verbose:
                print "Amplitude out of range:", amplitude
            return False

        if self[TYPE_KEY] in (gr.GR_SIN_WAVE, gr.GR_CONST_WAVE, gr.GR_GAUSSIAN, gr.GR_UNIFORM):
            self._src.set_amplitude(amplitude)
        elif self[TYPE_KEY] == "2tone":
            self._src1.set_amplitude(amplitude/2.0)
            self._src2.set_amplitude(amplitude/2.0)
        elif self[TYPE_KEY] == "sweep":
            self._src.set_k(amplitude)
        else:
            return True # Waveform not yet set

        if self._verbose:
            print "Set amplitude to:", amplitude
        return True

def get_options():
    usage="%prog: [options]"

    parser = OptionParser(option_class=eng_option, usage=usage)
    parser.add_option("-a", "--args", type="string", default="",
                      help="Device args, [default=%default]")
    parser.add_option("-A", "--antenna", type="string", default=None,
                      help="Select Rx Antenna where appropriate")
    parser.add_option("-s", "--samp-rate", type="eng_float", default=1e6,
                      help="Set sample rate (bandwidth) [default=%default]")
    parser.add_option("-g", "--gain", type="eng_float", default=None,
                      help="Set gain in dB (default is midpoint)")
    parser.add_option("-f", "--tx-freq", type="eng_float", default=None,
                      help="Set carrier frequency to FREQ [default=mid-point]",
                      metavar="FREQ")
    parser.add_option("-c", "--freq-corr", type="int", default=None,
                      help="Set carrier frequency correction [default=0]")
    parser.add_option("-x", "--waveform-freq", type="eng_float", default=0,
                      help="Set baseband waveform frequency to FREQ [default=%default]")
    parser.add_option("-y", "--waveform2-freq", type="eng_float", default=None,
                      help="Set 2nd waveform frequency to FREQ [default=%default]")
    parser.add_option("--sine", dest="type", action="store_const", const=gr.GR_SIN_WAVE,
                      help="Generate a carrier modulated by a complex sine wave",
                      default=gr.GR_SIN_WAVE)
    parser.add_option("--const", dest="type", action="store_const", const=gr.GR_CONST_WAVE,
                      help="Generate a constant carrier")
    parser.add_option("--offset", type="eng_float", default=0,
                      help="Set waveform phase offset to OFFSET [default=%default]")
    parser.add_option("--gaussian", dest="type", action="store_const", const=gr.GR_GAUSSIAN,
                      help="Generate Gaussian random output")
    parser.add_option("--uniform", dest="type", action="store_const", const=gr.GR_UNIFORM,
                      help="Generate Uniform random output")
    parser.add_option("--2tone", dest="type", action="store_const", const="2tone",
                      help="Generate Two Tone signal for IMD testing")
    parser.add_option("--sweep", dest="type", action="store_const", const="sweep",
                      help="Generate a swept sine wave")
    parser.add_option("", "--amplitude", type="eng_float", default=0.3,
                      help="Set output amplitude to AMPL (0.0-1.0) [default=%default]",
                      metavar="AMPL")
    parser.add_option("-v", "--verbose", action="store_true", default=False,
                      help="Use verbose console output [default=%default]")

    (options, args) = parser.parse_args()

    return (options, args)

# If this script is executed, the following runs. If it is imported,
# the below does not run.
def test_main():
    if gr.enable_realtime_scheduling() != gr.RT_OK:
        print "Note: failed to enable realtime scheduling, continuing"

    # Grab command line options and create top block
    try:
        (options, args) = get_options()
        tb = top_block(options, args)

    except RuntimeError, e:
        print e
        sys.exit(1)

    tb.start()
    raw_input('Press Enter to quit: ')
    tb.stop()
    tb.wait()

# Make sure to create the top block (tb) within a function:
# That code in main will allow tb to go out of scope on return,
# which will call the decontructor on radio and stop transmit.
# Whats odd is that grc works fine with tb in the __main__,
# perhaps its because the try/except clauses around tb.
if __name__ == "__main__":
    test_main()