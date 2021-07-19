import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { APIService } from '../api.service';
import { NotificationService } from '../notification.service';
import { UserData, Collection } from '../util/data-types'
import { ManagedSubs } from '../util/managed-subs';
import { Md5 } from 'ts-md5'

@Component({
  selector: 'app-user-page',
  templateUrl: './user-page.component.html',
  styleUrls: ['./user-page.component.css']
})
export class UserPageComponent extends ManagedSubs implements OnInit {

  public userID : number = null;
  public userData : UserData = null;
  public formData : {[key: string]: string | {[key: string]: string}} = {};

  public possibleCollections : {[collectionID: number]: Collection} = {};

  public specificCollectionID : number = -1;

  @ViewChild('formContainer') formContainer : ElementRef;

  objectKeys(obj : any) { 
    if(obj) {
      return Object.keys(obj);
    } else {
      return null;
    }
  }

  constructor(private notifier : NotificationService, public api : APIService, private route: ActivatedRoute, private router : Router) {
    super();
  }

  addToForm(key : string, value : any) {
    this.formData[key] = <string>value;
  }

  addCollectionDetailToForm(collection : number, value : number) {
    if(this.formData['collection_details'] == undefined) {
      this.formData['collection_details'] = {}
    }
    this.formData['collection_details'][''+collection] = ''+value;
  }

  sendForm() {
    if(this.formData['password1'] != undefined) {
      if(this.formData['password2'] == undefined) {
        this.notifier.failed('Please confirm your password');
        return;
      }
      if(this.formData['password2'] != this.formData['password1']) {
        this.notifier.failed('The passwords do not match');
        return;
      }
      this.formData['password'] = ''+Md5.hashStr(this.formData['password1'] as string);
      this.formData['password1'] = '';
      this.formData['password2'] = '';
    }
    this.api.updateUser(this.userID, this.formData).then(
      data => {
      }, error => {
      }
    );
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.userID = +params['id'];

      this.manageSub('userinfo', this.api.data["user_man"].get(this.userID).subscribe(
        userdata => {
          if(userdata) {
            let splittedDate = userdata.data.time_limit.split(' ');
            userdata.data.time_limit = splittedDate[0];
            this.userData = userdata.data;
            console.log(this.userData);
          }
        }
      ));
    }));
    this.manageSub('collectionData', this.api.data["collections"].get().subscribe(data => {
      if(data) {
        data.data.forEach(collection => {
          this.possibleCollections[collection.id] = collection;
        });
      }
    }))
  }

}
