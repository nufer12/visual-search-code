import { Component, OnInit, ElementRef, ViewChild, HostListener } from '@angular/core';
import { IndexData, Search, Retrieval, SearchResult } from '../util/data-types';
import { APIService } from '../api.service';
import { ManagedSubs } from '../util/managed-subs';
import { Router, ActivatedRoute } from '@angular/router';
import { NotificationService } from '../notification.service';
import { FavoriteService } from '../favorite.service';
import { DomSanitizer, SafeStyle } from '@angular/platform-browser';

@Component({
  selector: 'app-review',
  templateUrl: './review.component.html',
  styleUrls: ['./review.component.scss']
})
export class ReviewComponent extends ManagedSubs implements OnInit {

  collectionID : number;
  searchIDs : string[]; // yes, this is a string, because can be "all"
  indexIDs : string[];
  maxRetrievals : number;

  indices : IndexData[] = null;
  searches : Search[] = null;

  retrievalPairs : Retrieval[] = null;
  startedWithPairs : number = 0;

  currentPercentage : number = null;
  currentPercentageStyle : SafeStyle = null;

  @ViewChild('mainContainer') mainContainer : ElementRef;
  @ViewChild('selectionContainer') selectionContainer : ElementRef;

  activeSearchResult : SearchResult = null;
  activeQuery : SearchResult = null;
  activeIndex: number = null;

  public paginationSettings : number[] = [0, 0];
  public filterScheme = [
    {type: "text", name: "query", placeholder: 'Keyword'}
  ]

  constructor(private favs: FavoriteService, private notifier : NotificationService, public api : APIService, private route: ActivatedRoute, private router : Router, private _sanitizer: DomSanitizer) {
    super();
  }

  isFavorite : any = false;

  ngOnInit() {


    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];

      this.manageSub('get_params', this.route.queryParams.subscribe(gparams => {
        // this.searchIDs = (gparams['search'] == null) ? [] : gparams['search'].split(',');
        this.searchIDs = [];
        this.indexIDs = (gparams['index'] == null) ? [] : gparams['index'].split(',');
        this.maxRetrievals = (gparams['max'] == null) ? 20 : +gparams['max'];
        this.refreshOpenResults();

      }));

      this.manageSub('indices', this.api.data["indices"].get(this.collectionID).subscribe(
        list => {
          if(list) {
            this.indices = list.data;
          }
        }
      ));

      this.manageSub('searches', this.api.data['searches'].get(this.collectionID).subscribe(
        data => {
          if(data) {
            this.searches = data.data;
          }
        }
      ));

      this.manageSub('localchange', this.favs.localChanges.subscribe(kp => {
        this.recalcFav();
      }))
    }));

  }

  @HostListener('window:keypress', ['$event'])
  keyPressEvent(ev: KeyboardEvent) {
    if(ev.keyCode == 13) {
      this.voteOnActive(1);
    }
    if(ev.keyCode == 46) {
      this.voteOnActive(-1);
    }
  }

  refreshOpenResults() {
    this.manageSub('retrievals', this.api.getUnreviewed(this.collectionID, this.indexIDs, this.searchIDs, this.maxRetrievals).subscribe(
      retr => {
        if(retr != null) {
          this.retrievalPairs = retr.filter(ret => {
            return ret.vote == 0;
          });
          this.startedWithPairs = retr.length;
          this.nextSample();
        }
      }
    ))
  }

  refreshParams() {
    let checkedIndices = [];
    this.selectionContainer.nativeElement.querySelectorAll('input[name="selection-index"]:checked').forEach(el => {
      checkedIndices.push(el.value);
    });
    let checkedSearches = [];
    // this.selectionContainer.nativeElement.querySelectorAll('input[name="selection-search"]:checked').forEach(el => {
    //   checkedSearches.push(el.value);
    // });
    let newQueryParams = {
      "max": this.maxRetrievals
    };
    if(checkedIndices.length > 0) {
      newQueryParams['index'] = checkedIndices.join(',');
    }
    // if(checkedSearches.length > 0) {
    //   newQueryParams['search'] = checkedSearches.join(',');
    // }
    this.router.navigate([], {queryParams: newQueryParams});
  }

  nextSample() {

    if(this.retrievalPairs.length == 0) {
      this.activeSearchResult = null;
      this.activeQuery = null;
      return;
    }

    let new_ind = Math.floor(Math.random() * Math.floor(this.retrievalPairs.length));
    let nextObj = this.retrievalPairs[new_ind];

    this.retrievalPairs = this.retrievalPairs.filter(el => {
      return el.id != nextObj.id;
    })

    this.activeSearchResult = nextObj;
    this.activeSearchResult.refined_searchbox = null;
    this.activeQuery = Object.assign({}, nextObj);
    this.activeQuery.id = -1 * nextObj.id; // you need another id
    this.activeQuery.image_id = nextObj.query_image_id;
    this.activeQuery.filename = nextObj.query_filename;
    this.activeQuery.box_data = nextObj.query_bbox;
    this.activeQuery.refined_searchbox = null;

    this.currentPercentage = 100 - 100 * (this.retrievalPairs.length + 1) / this.startedWithPairs;
    this.currentPercentageStyle = this._sanitizer.bypassSecurityTrustStyle(this.currentPercentage+'%');

    this.isFavorite = false;
    
    this.recalcFav();
  }

  voteOnActive(vote: number) {

    if(this.activeSearchResult == null) {
      return;
    }

    this.mainContainer.nativeElement.classList.remove('voted-up');
    this.mainContainer.nativeElement.classList.remove('voted-down');

    this.api.voteForResult(this.activeSearchResult.id, vote).then(data => {

      if(vote == 1) {
        this.mainContainer.nativeElement.classList.add('voted-up');
      } else {
        this.mainContainer.nativeElement.classList.add('voted-down');
      }
      this.nextSample();
    }, error => {
      // console.log('not voted')
    })
  }

  toggleFavorite() {
    this.favs.isFavorite(this.activeSearchResult.id, this.activeSearchResult.search_id).then(
      isFav => {
        if(isFav) {
          this.favs.removeFavorite(this.activeSearchResult.id, this.activeSearchResult.search_id).then(() => {
            // this.recalcFav();
          });
        } else {
          this.favs.addFavorite(this.activeSearchResult.id, this.activeSearchResult.search_id).then(() => {
            // this.recalcFav();
          });
        }
      }
    )
  }

  recalcFav() {
    if(this.activeSearchResult) {
      this.favs.isFavorite(this.activeSearchResult.id, this.activeSearchResult.search_id).then(
        isFav => {
          this.isFavorite = isFav;
        }
      );
    }
    
  }

}
