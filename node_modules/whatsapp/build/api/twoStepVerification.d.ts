/**
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 * All rights reserved.
 *
 * This source code is licensed under the license found in the
 * LICENSE file in the root directory of this source tree.
 */
import { RequesterResponseInterface } from '../types/requester';
import BaseAPI from './base';
import * as tsv from '../types/twoStepVerification';
export default class TwoStepVerificationAPI extends BaseAPI implements tsv.TwoStepVerificationClass {
    private readonly commonMethod;
    private readonly commonEndpoint;
    setPin(pin: number): Promise<RequesterResponseInterface<tsv.SetPinResponseObject>>;
}
