#Embedded file name: /Users/versonator/Hudson/live/Projects/AppLive/Resources/MIDI Remote Scripts/Push/SpecialChanStripComponent.py
from _Framework.Util import flatten
from _Framework import Task
from _Framework.SubjectSlot import subject_slot, subject_slot_group
from _Framework.ChannelStripComponent import ChannelStripComponent
from _Framework.DisplayDataSource import DisplayDataSource
from _Framework.InputControlElement import ParameterSlot
from MessageBoxComponent import Messenger
from consts import MessageBoxText
import consts
import Live
TRACK_FOLD_DELAY = 0.5
TRACK_PARAMETER_NAMES = ('Volume', 'Pan', 'Send A', 'Send B', 'Send C', 'Send D', 'Send E', 'Send F', 'Send G', 'Send H', 'Send I', 'Send J', 'Send K', 'Send L')

def param_value_to_graphic(param, graphic):
    if param != None:
        param_range = param.max - param.min
        graph_range = len(graphic) - 1
        value = int((param.value - param.min) / param_range * graph_range)
        graphic_display_string = graphic[value]
    else:
        graphic_display_string = ' '
    return graphic_display_string


class SpecialChanStripComponent(ChannelStripComponent, Messenger):
    """
    Channel strip component with press & hold mute solo and stop
    buttons
    """

    def __init__(self, *a, **k):
        super(SpecialChanStripComponent, self).__init__(*a, **k)
        self.empty_color = 'Option.Unused'
        self._invert_mute_feedback = True
        self._delete_button = None
        self._duplicate_button = None
        self._selector_button = None
        self._track_parameter_name_sources = [ DisplayDataSource(' ') for _ in xrange(14) ]
        self._track_parameter_data_sources = [ DisplayDataSource(' ') for _ in xrange(14) ]
        self._track_parameter_graphic_sources = [ DisplayDataSource(' ') for _ in xrange(14) ]
        self._on_return_tracks_changed.subject = self.song()
        self._on_selected_track_changed.subject = self.song().view
        self._fold_task = self._tasks.add(Task.sequence(Task.wait(TRACK_FOLD_DELAY), Task.run(self._do_fold_track)))
        self._cue_volume_slot = self.register_disconnectable(ParameterSlot())

    def set_volume_control(self, control):
        if control != None:
            control.mapping_sensitivity = consts.CONTINUOUS_MAPPING_SENSITIVITY
        super(SpecialChanStripComponent, self).set_volume_control(control)

    def set_pan_control(self, control):
        if control != None:
            control.mapping_sensitivity = consts.CONTINUOUS_MAPPING_SENSITIVITY
        super(SpecialChanStripComponent, self).set_pan_control(control)

    def set_send_controls(self, controls):
        if controls != None:
            for control in controls:
                if control != None:
                    control.mapping_sensitivity = consts.CONTINUOUS_MAPPING_SENSITIVITY

        super(SpecialChanStripComponent, self).set_send_controls(controls)

    def set_cue_volume_control(self, control):
        if control != None:
            control.mapping_sensitivity = consts.CONTINUOUS_MAPPING_SENSITIVITY
        self._cue_volume_slot.control = control

    def set_delete_button(self, delete_button):
        self._delete_button = delete_button

    def set_duplicate_button(self, duplicate_button):
        self._duplicate_button = duplicate_button

    def set_selector_button(self, selector_button):
        self._selector_button = selector_button

    def track_parameter_data_sources(self, index):
        return self._track_parameter_data_sources[index]

    def track_parameter_graphic_sources(self, index):
        return self._track_parameter_graphic_sources[index]

    def track_parameter_name_sources(self, index):
        return self._track_parameter_name_sources[index]

    def get_track(self):
        return self._track

    def set_track(self, track):
        super(SpecialChanStripComponent, self).set_track(track)
        self._update_track_listeners()
        self._update_parameter_name_sources()
        self._update_parameter_values()

    @subject_slot('return_tracks')
    def _on_return_tracks_changed(self):
        self._update_track_listeners()
        self._update_parameter_name_sources()
        self._update_parameter_values()

    @subject_slot('selected_track')
    def _on_selected_track_changed(self):
        self._update_track_name_data_source()

    def _update_track_listeners(self):
        mixer = self._track.mixer_device if self._track else None
        sends = mixer.sends if mixer and self._track != self.song().master_track else ()
        cue_volume = mixer.cue_volume if self._track == self.song().master_track else None
        self._cue_volume_slot.parameter = cue_volume
        self._on_volume_value_changed.subject = mixer and mixer.volume
        self._on_panning_value_changed.subject = mixer and mixer.panning
        self._on_sends_value_changed.replace_subjects(sends)

    def _update_parameter_name_sources(self):
        num_params = self._track and len(self._track.mixer_device.sends) + 2
        for index, source in enumerate(self._track_parameter_name_sources):
            if index < num_params:
                source.set_display_string(TRACK_PARAMETER_NAMES[index])
            else:
                source.set_display_string(' ')

    def _update_track_name_data_source(self):
        if self._track_name_data_source:
            if self._track != None:
                selected = self._track == self.song().view.selected_track
                prefix = consts.CHAR_SELECT if selected else ''
                self._track_name_data_source.set_display_string(prefix + self._track.name)
            else:
                self._track_name_data_source.set_display_string(' ')

    def _select_value(self, value):
        if self.is_enabled() and self._track:
            if self._duplicate_button and self._duplicate_button.is_pressed() and value:
                self._do_duplicate_track(self._track)
            elif self._delete_button and self._delete_button.is_pressed() and value:
                self._do_delete_track(self._track)
            else:
                super(SpecialChanStripComponent, self)._select_value(value)
                if self._selector_button and self._selector_button.is_pressed() and value:
                    self._do_select_track(self._track)
                if not self._shift_pressed:
                    if self._track.is_foldable and self._select_button.is_momentary() and value != 0:
                        self._fold_task.restart()
                    else:
                        self._fold_task.kill()

    def _do_delete_track(self, track):
        try:
            track_index = list(self.song().tracks).index(track)
            name = track.name
            self.song().delete_track(track_index)
            self.show_notification(MessageBoxText.DELETE_TRACK % name)
        except RuntimeError:
            self.expect_dialog(MessageBoxText.TRACK_DELETE_FAILED)
        except ValueError:
            pass

    def _do_duplicate_track(self, track):
        try:
            track_index = list(self.song().tracks).index(track)
            self.song().duplicate_track(track_index)
            self.show_notification(MessageBoxText.DUPLICATE_TRACK % track.name)
        except Live.Base.LimitationError:
            self.expect_dialog(MessageBoxText.TRACK_LIMIT_REACHED)
        except RuntimeError:
            self.expect_dialog(MessageBoxText.TRACK_DUPLICATION_FAILED)
        except ValueError:
            pass

    def _do_select_track(self, track):
        pass

    def _do_fold_track(self):
        if self.is_enabled() and self._track != None and self._track.is_foldable:
            self._track.fold_state = not self._track.fold_state

    @subject_slot('value')
    def _on_volume_value_changed(self):
        if self.is_enabled() and self._track != None:
            param = self._track.mixer_device.volume
            text = self._track_parameter_data_sources[0]
            graph = self._track_parameter_graphic_sources[0]
            text.set_display_string(str(param))
            graph.set_display_string(param_value_to_graphic(param, consts.GRAPH_VOL))

    @subject_slot('value')
    def _on_panning_value_changed(self):
        if self.is_enabled() and self._track != None:
            param = self._track.mixer_device.panning
            text = self._track_parameter_data_sources[1]
            graph = self._track_parameter_graphic_sources[1]
            text.set_display_string(str(param))
            graph.set_display_string(param_value_to_graphic(param, consts.GRAPH_PAN))

    @subject_slot_group('value')
    def _on_sends_value_changed(self, send):
        if self.is_enabled() and self._track != None and self._track != self.song().master_track and send in list(self._track.mixer_device.sends):
            index = list(self._track.mixer_device.sends).index(send) + 2
            text = self._track_parameter_data_sources[index]
            graph = self._track_parameter_graphic_sources[index]
            text.set_display_string(str(send))
            graph.set_display_string(param_value_to_graphic(send, consts.GRAPH_VOL))

    def _update_parameter_values(self):
        for source in flatten(zip(self._track_parameter_data_sources, self._track_parameter_graphic_sources)):
            source.set_display_string(' ')

        self._on_volume_value_changed()
        self._on_panning_value_changed()
        if self._track and self._track != self.song().master_track:
            map(self._on_sends_value_changed, self._track.mixer_device.sends)