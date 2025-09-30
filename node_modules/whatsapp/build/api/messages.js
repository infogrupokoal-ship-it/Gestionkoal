"use strict";

/**
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 * All rights reserved.
 *
 * This source code is licensed under the license found in the
 * LICENSE file in the root directory of this source tree.
 */
var __importDefault = this && this.__importDefault || function (mod) {
  return mod && mod.__esModule ? mod : {
    "default": mod
  };
};
Object.defineProperty(exports, "__esModule", {
  value: true
});
const base_1 = __importDefault(require("./base"));
const enums_1 = require("../types/enums");
const logger_1 = __importDefault(require("../logger"));
const LIB_NAME = 'MESSAGES_API';
const LOG_LOCAL = false;
const LOGGER = new logger_1.default(LIB_NAME, process.env.DEBUG === 'true' || LOG_LOCAL);
class MessagesAPI extends base_1.default {
  constructor() {
    super(...arguments);
    this.commonMethod = enums_1.HttpMethodsEnum.Post;
    this.commonEndpoint = 'messages';
  }
  bodyBuilder(type, payload, toNumber, replyMessageId) {
    const body = {
      messaging_product: 'whatsapp',
      recipient_type: 'individual',
      to: toNumber,
      type: type,
      [type]: payload
    };
    if (replyMessageId) body['context'] = {
      message_id: replyMessageId
    };
    return body;
  }
  send(body) {
    return this.client.sendCAPIRequest(this.commonMethod, this.commonEndpoint, this.config[enums_1.WAConfigEnum.RequestTimeout], body);
  }
  async audio(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Audio, body, recipient.toString(), replyMessageId)));
  }
  async contacts(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Contacts, body, recipient.toString(), replyMessageId)));
  }
  async document(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Document, body, recipient.toString(), replyMessageId)));
  }
  async image(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Image, body, recipient.toString(), replyMessageId)));
  }
  async interactive(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Interactive, body, recipient.toString(), replyMessageId)));
  }
  async location(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Location, body, recipient.toString(), replyMessageId)));
  }
  async sticker(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Sticker, body, recipient.toString(), replyMessageId)));
  }
  async template(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Template, body, recipient.toString(), replyMessageId)));
  }
  async text(body, recipient, replyMessageId) {
    LOGGER.log(body);
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Text, body, recipient.toString(), replyMessageId)));
  }
  async video(body, recipient, replyMessageId) {
    return this.send(JSON.stringify(this.bodyBuilder(enums_1.MessageTypesEnum.Video, body, recipient.toString(), replyMessageId)));
  }
  async status(body) {
    const mp = {
      messaging_product: 'whatsapp'
    };
    const bodyToSend = Object.assign(mp, body);
    return this.send(JSON.stringify(bodyToSend));
  }
}
exports.default = MessagesAPI;
module.exports = exports.default;