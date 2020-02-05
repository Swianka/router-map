import $ from 'jquery';
import {dataUpdate, handleDeleteBtnClick} from './base-setup'
import {} from './settings-change'

import 'ol/ol.css';

import '../css/index.css';
import '../css/map.css';

import * as map from './map-creation'
import {handleSaveSettingsBtnClick} from './settings-change'

$('#delete_btn').click(handleDeleteBtnClick(map.refresh));

window.setInterval(dataUpdate(map.refresh), 100000);

$('#save_settings_btn').click(handleSaveSettingsBtnClick(map.refresh));

